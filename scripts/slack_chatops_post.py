from os import environ
from json import dumps
from typing import Optional, List, Dict

from slack.web.client import WebClient
from slack.web.classes.blocks import ImageBlock, SectionBlock, ActionsBlock
from slack.web.classes.objects import MarkdownTextObject
from slack.web.classes.elements import ButtonElement
from slack.web.classes.messages import Message

def details_builder(project: str, project_url:str, user: str, branch: str, issue_id: str, issue_url: str) -> SectionBlock:
    project_field: MarkdownTextObject = MarkdownTextObject(text=f"*Project Repo:*\n<{project_url}|{project}>")
    project_field: MarkdownTextObject = MarkdownTextObject(text=f"*Issue ID:*\n<{issue_url}|#{issue_id}>")
    branch_field: MarkdownTextObject = MarkdownTextObject(text=f"*Ref:*\n{branch}")
    from_user_field: MarkdownTextObject = MarkdownTextObject(text=f"*From:*\n{user}")
    image_accessory: ImageBlock = ImageBlock(image_url="https://avatars0.githubusercontent.com/u/44036562", alt_text="GitHub Action")
    return SectionBlock(fields=[project_field, branch_field, from_user_field], accessory=image_accessory)

def status_builder(build_status: Optional[str] = None, test_status: Optional[str] = None, deploy_status: Optional[str] = None) -> SectionBlock:
    fields: List[MarkdownTextObject] = []
    if build_status:
        text = "*Build*: "
        text += ":heavy_check_mark:" if build_status == "PASS" else ":x:"
        fields.append(MarkdownTextObject(text=text))
    if test_status:
        text = "*Tests*: "
        text += ":heavy_check_mark:" if test_status == "PASS" else ":x:"
        fields.append(MarkdownTextObject(text=text))
    if deploy_status:
        text = "*Deploy*: "
        text += ":heavy_check_mark:" if deploy_status == "PASS" else ":x:"
        fields.append(MarkdownTextObject(text=text))
    return SectionBlock(fields=fields)

def message_builder(title: str, blocks: List[ActionsBlock|SectionBlock]) -> Message:
    return Message(text=f"*{title}*", blocks=blocks)

def buttons_builder(message_type: str, repository: str, branch: str, run_id: str, workflow: Optional[str] = None) -> ActionsBlock:
    elements: List[ButtonElement] = []
    if message_type == "ERROR":
        retry_value: Dict = { "url_call": f"/repos/{repository}/actions/runs/{run_id}/rerun" }
        elements.append(ButtonElement(text="Retry", action_id="retry", value=dumps(retry_value), style="default"))
    elif message_type == "REQUEST":
        approve_payload: Dict = { "ref": branch, "inputs": { "is_approved": "1" } }
        approve_value: Dict = { "url_call": f"/repos/{repository}/actions/workflows/{workflow}/dispatches", "payload": dumps(approve_payload)}
        elements.append(ButtonElement(text="Approuve", action_id="approval", value=dumps(approve_value), style="primary"))
        deny_payload: Dict = { "ref": branch, "inputs": { "is_approved": "0" } }
        deny_value: Dict = { "url_call": f"/repos/{repository}/actions/workflows/{workflow}/dispatches", "payload": dumps(deny_payload)}
        elements.append(ButtonElement(text="Deny", action_id="denial", value=dumps(deny_value), style="danger"))
    return ActionsBlock(elements=elements)

def main():
    # Slack API Token
    slack_api_token: str = environ['SLACK_API_TOKEN']
    # Slack Channel name or ID
    slack_channel: str = environ['SLACK_CHANNEL']
    # App or User triggering the action
    user: str = environ['GITHUB_ACTOR']
    # Repository name user/project
    repository: str = environ['GITHUB_REPOSITORY']
    # Optional Workflow file name to manually start
    workflow: Optional[str] = environ.get('WORKFLOW', None)
    # Optional Workflow ID to re-run
    run_id: str = environ['GITHUB_RUN_ID']
    # Branch/ref name
    branch: str = environ.get('GITHUB_REF', "")
    # Message type, "ERROR" or "REQUEST"
    message_type: str = environ['MESSAGE_TYPE']
    # Message title
    title: str = environ['TITLE']
    # Project name
    project: str = environ['PROJECT_NAME']
    # GitHub project URL
    project_url: str = f"{environ['GITHUB_SERVER_URL']}/{repository}/tree/{branch}"
    # Hub Issue ID
    issue_id: str = environ['ISSUE_ID']
    # Hub Issue URL
    issue_url: str = f"https://hub.toumoro.com/issues/{issue_id}"
    # Optional Build status, "PASS" or "FAIL"
    build_status: Optional[str] = environ.get('BUILD_STATUS', None)
    # Optional Test status, "PASS" or "FAIL"
    test_status: Optional[str] = environ.get('TEST_STATUS', None)
    # Optional Deploy status, "PASS" or "FAIL"
    deploy_status: Optional[str] = environ.get('DEPLOY_STATUS', None)

    blocks: List[ActionsBlock|SectionBlock] = []

    # Build project information section
    blocks.append(details_builder(project=project, project_url=project_url, user=user, branch=branch, issue_id=issue_id, issue_url=issue_url))
    # Build workflow information section
    blocks.append(status_builder(build_status=build_status, test_status=test_status, deploy_status=deploy_status))
    # Build interactive section if needed
    if message_type in ['ERROR', 'REQUEST']:
        blocks.append(buttons_builder(message_type=message_type, repository=repository, branch=branch, run_id=run_id, workflow=workflow))
    # Build message
    message: Dict = message_builder(title=title, blocks=blocks).to_dict()
    # Sending message
    client: WebClient = WebClient(token=slack_api_token)
    client.chat_postMessage(channel=slack_channel, **message)

if __name__ == "__main__":
    main()