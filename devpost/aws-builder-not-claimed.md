Not applicable - we are not submitting for the AWS Builder Mini Challenge.

No AWS service is incorporated in this project. The MCP server is self-hosted, and
nothing in the server, the content tooling, the test harness or the dependency list
imports or calls boto3, Bedrock, SageMaker, AgentCore, Strands or Kiro. The only AWS
we encountered was the private CodeArtifact repository hosting the alexa-ai CLI, and
we were never granted the IAM role needed to reach it - friction log items 1 and 2.
