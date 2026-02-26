"""S3 + CloudFront for serving the SvelteKit SPA.

Architecture:
  Browser → CloudFront → S3 (static files)
                       → API Gateway (proxied via /api/* behavior)

Key design decisions:
  - OAC (not OAI) so S3 returns 404 (not 403) for missing files.
    This lets us use a 404→index.html error response for SPA routing
    without intercepting legitimate API Gateway 403s (auth errors).
  - ListBucket permission ensures S3 returns 404 instead of 403 for missing keys.
  - /api/* behavior proxies to REST API Gateway with caching disabled.
  - Error response TTL=0 prevents CloudFront from caching 404→index.html redirects.
  - Frontend build is deployed to S3 only if the build/ directory exists.
"""

import os

from aws_cdk import Duration, RemovalPolicy, aws_s3 as s3, aws_s3_deployment as s3deploy, aws_cloudfront as cloudfront, aws_cloudfront_origins as origins, aws_iam as iam
from constructs import Construct


class Frontend(Construct):
    def __init__(self, scope: Construct, id: str, *, rest_api):
        super().__init__(scope, id)

        bucket = s3.Bucket(
            self, "SiteBucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        # OAC gives CloudFront access to S3 without making the bucket public
        oac = cloudfront.S3OriginAccessControl(self, "SiteOAC")
        s3_origin = origins.S3BucketOrigin.with_origin_access_control(bucket, origin_access_control=oac)

        # ListBucket is needed so S3 returns 404 (not 403) for missing keys
        bucket.add_to_resource_policy(iam.PolicyStatement(
            actions=["s3:GetObject", "s3:ListBucket"],
            resources=[bucket.bucket_arn, bucket.arn_for_objects("*")],
            principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
        ))

        self.distribution = cloudfront.Distribution(
            self, "SiteDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=s3_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            additional_behaviors={
                # Proxy API calls to REST API Gateway — no caching, pass all headers
                "/api/*": cloudfront.BehaviorOptions(
                    origin=origins.RestApiOrigin(rest_api),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                ),
            },
            default_root_object="index.html",
            # SPA routing: any 404 from S3 serves index.html so client-side router handles it
            error_responses=[
                cloudfront.ErrorResponse(http_status=404, response_http_status=200, response_page_path="/index.html", ttl=Duration.seconds(0)),
            ],
        )

        # Deploy frontend build to S3 (only if build exists — skipped on first CDK deploy)
        frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "build")
        if os.path.isdir(frontend_dir):
            s3deploy.BucketDeployment(
                self, "SiteDeployment",
                sources=[s3deploy.Source.asset(frontend_dir)],
                destination_bucket=bucket,
                distribution=self.distribution,  # invalidates CloudFront cache after deploy
            )
