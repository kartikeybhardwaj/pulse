#!/usr/bin/env python3
import aws_cdk as cdk
from stack import PulseStack

app = cdk.App()
PulseStack(app, "PulseStack")
app.synth()
