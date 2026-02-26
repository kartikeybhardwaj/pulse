"""WebSocket API Gateway for real-time poll updates.

Three Lambda handlers:
  - $connect: stores connection ID in DynamoDB
  - $disconnect: cleans up connection + all its subscriptions
  - subscribe: links a connection to a poll ID for broadcast

When a vote/edit/close happens, the REST Lambda uses the API Gateway
Management API to push updates to all connections subscribed to that poll.
The REST Lambda needs execute-api:ManageConnections permission and the
WS_API_ENDPOINT env var to know where to post.
"""

from aws_cdk import Stack, aws_lambda as _lambda, aws_apigatewayv2 as apigwv2, aws_apigatewayv2_integrations as integrations, aws_iam as iam
from constructs import Construct


class WebSocketApi(Construct):
    def __init__(self, scope: Construct, id: str, *, table, rest_fn, backend_dir, common_lambda_props):
        super().__init__(scope, id)

        # Each WS route gets its own lightweight Lambda
        ws_connect_fn = _lambda.Function(self, "WsConnectLambda", handler="handlers.ws_connect.handler", code=_lambda.Code.from_asset(backend_dir), **common_lambda_props)
        ws_disconnect_fn = _lambda.Function(self, "WsDisconnectLambda", handler="handlers.ws_disconnect.handler", code=_lambda.Code.from_asset(backend_dir), **common_lambda_props)
        ws_subscribe_fn = _lambda.Function(self, "WsSubscribeLambda", handler="handlers.ws_subscribe.handler", code=_lambda.Code.from_asset(backend_dir), **common_lambda_props)

        for fn in [ws_connect_fn, ws_disconnect_fn, ws_subscribe_fn]:
            table.grant_read_write_data(fn)

        self.api = apigwv2.WebSocketApi(
            self, "PulseWsApi",
            api_name="PulseWS",
            connect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration("ConnectInt", ws_connect_fn),
            ),
            disconnect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration("DisconnectInt", ws_disconnect_fn),
            ),
        )
        # Custom route — clients send {"action": "subscribe", "pollId": "abc123"}
        self.api.add_route("subscribe", integration=integrations.WebSocketLambdaIntegration("SubscribeInt", ws_subscribe_fn))

        self.stage = apigwv2.WebSocketStage(self, "ProdStage", web_socket_api=self.api, stage_name="prod", auto_deploy=True)

        # The REST Lambda broadcasts poll updates by POSTing to @connections/{connId}
        # via the API Gateway Management API — needs explicit permission
        ws_manage_arn = Stack.of(self).format_arn(
            service="execute-api", resource=self.api.api_id, resource_name="prod/POST/@connections/*",
        )
        rest_fn.add_to_role_policy(iam.PolicyStatement(actions=["execute-api:ManageConnections"], resources=[ws_manage_arn]))
        rest_fn.add_environment("WS_API_ENDPOINT", f"https://{self.api.api_id}.execute-api.{Stack.of(self).region}.amazonaws.com/prod")
