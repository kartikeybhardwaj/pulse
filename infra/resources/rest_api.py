"""REST API Gateway + Lambda functions for auth and poll operations.

Two Lambdas behind one API Gateway:
  - AuthFn: handles /api/auth/* (signup, verify, signin, forgot, reset, me)
  - RestFn: handles /api/polls/* (CRUD, voting, listing)

Both Lambdas read the JWT signing secret from SSM Parameter Store.
AuthFn additionally has SES permissions for sending verification/reset emails.

Rate limiting is enforced per-endpoint at the API Gateway stage level.
Auth endpoints have tighter limits (2-10 req/s) to prevent brute force.
Poll endpoints have moderate limits (5-30 req/s).

SES_FROM_EMAIL env var controls the sender address (must be SES-verified).
"""

import os

from aws_cdk import aws_apigateway as apigw, aws_lambda as _lambda, aws_iam as iam, aws_ssm as ssm
from constructs import Construct


class RestApi(Construct):
    def __init__(self, scope: Construct, id: str, *, table, backend_dir, common_lambda_props, common_env):
        super().__init__(scope, id)

        # JWT secret is created once manually (see README) and referenced here
        jwt_param_name = "/pulse/jwt-secret"
        jwt_secret = ssm.StringParameter.from_string_parameter_name(self, "JwtSecret", jwt_param_name)

        # Poll CRUD + voting Lambda — also verifies JWT tokens for user identity
        self.rest_fn = _lambda.Function(
            self, "PollsLambda",
            handler="handlers.rest_api.handler",
            code=_lambda.Code.from_asset(backend_dir),
            **{**common_lambda_props, "environment": {**common_env, "JWT_SECRET_PARAM": jwt_param_name}},
        )
        table.grant_read_write_data(self.rest_fn)
        jwt_secret.grant_read(self.rest_fn)

        # Auth Lambda — signup, signin, email verification, password reset
        ses_from_email = os.environ.get("SES_FROM_EMAIL", "no-reply@example.com")
        self.auth_fn = _lambda.Function(
            self, "AuthLambda",
            handler="handlers.auth.handler",
            code=_lambda.Code.from_asset(backend_dir),
            **{**common_lambda_props, "environment": {
                **common_env, "SES_FROM_EMAIL": ses_from_email, "JWT_SECRET_PARAM": jwt_param_name,
            }},
        )
        table.grant_read_write_data(self.auth_fn)
        jwt_secret.grant_read(self.auth_fn)
        self.auth_fn.add_to_role_policy(iam.PolicyStatement(actions=["ses:SendEmail"], resources=["*"]))

        # API Gateway with per-endpoint rate limiting
        rest_integration = apigw.LambdaIntegration(self.rest_fn)
        auth_integration = apigw.LambdaIntegration(self.auth_fn)

        self.api = apigw.RestApi(
            self, "PulseRestApi",
            rest_api_name="PulseREST",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
            deploy_options=apigw.StageOptions(
                throttling_rate_limit=50,
                throttling_burst_limit=100,
                method_options={
                    # Auth — tight limits to prevent brute force / abuse
                    "/api/auth/signup/POST": apigw.MethodDeploymentOptions(throttling_rate_limit=5, throttling_burst_limit=10),
                    "/api/auth/signin/POST": apigw.MethodDeploymentOptions(throttling_rate_limit=10, throttling_burst_limit=20),
                    "/api/auth/verify/POST": apigw.MethodDeploymentOptions(throttling_rate_limit=5, throttling_burst_limit=10),
                    "/api/auth/resend/POST": apigw.MethodDeploymentOptions(throttling_rate_limit=2, throttling_burst_limit=5),
                    "/api/auth/forgot/POST": apigw.MethodDeploymentOptions(throttling_rate_limit=2, throttling_burst_limit=5),
                    "/api/auth/reset/POST": apigw.MethodDeploymentOptions(throttling_rate_limit=5, throttling_burst_limit=10),
                    # Polls — moderate limits
                    "/api/polls/POST": apigw.MethodDeploymentOptions(throttling_rate_limit=10, throttling_burst_limit=20),
                    "/api/polls/GET": apigw.MethodDeploymentOptions(throttling_rate_limit=30, throttling_burst_limit=60),
                    "/api/polls/{pollId}/GET": apigw.MethodDeploymentOptions(throttling_rate_limit=30, throttling_burst_limit=60),
                    "/api/polls/{pollId}/vote/POST": apigw.MethodDeploymentOptions(throttling_rate_limit=20, throttling_burst_limit=40),
                    "/api/polls/{pollId}/PUT": apigw.MethodDeploymentOptions(throttling_rate_limit=5, throttling_burst_limit=10),
                    "/api/polls/{pollId}/PATCH": apigw.MethodDeploymentOptions(throttling_rate_limit=5, throttling_burst_limit=10),
                    "/api/polls/{pollId}/DELETE": apigw.MethodDeploymentOptions(throttling_rate_limit=5, throttling_burst_limit=10),
                },
            ),
        )

        # All routes live under /api/ so CloudFront can proxy /api/* to this gateway
        api_resource = self.api.root.add_resource("api")

        # Auth routes — all POST except /me which is GET
        auth_resource = api_resource.add_resource("auth")
        for name in ["signup", "signin", "verify", "resend", "forgot", "reset"]:
            auth_resource.add_resource(name).add_method("POST", auth_integration)
        auth_resource.add_resource("me").add_method("GET", auth_integration)

        # Poll routes
        polls = api_resource.add_resource("polls")
        polls.add_method("GET", rest_integration)   # list (recent / mine)
        polls.add_method("POST", rest_integration)  # create

        poll = polls.add_resource("{pollId}")
        poll.add_method("GET", rest_integration)     # get with results
        poll.add_method("DELETE", rest_integration)  # delete (creator only)
        poll.add_method("PUT", rest_integration)     # edit (creator only)
        poll.add_method("PATCH", rest_integration)   # close/reopen (creator only)
        poll.add_resource("vote").add_method("POST", rest_integration)  # cast/switch/undo vote
