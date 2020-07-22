from os import environ
from json import dumps
from pprint import PrettyPrinter
from typing import Optional, List, Dict, Union

from slack.errors import SlackApiError
from slack.web.client import WebClient
from slack.web.classes.blocks import SectionBlock, ActionsBlock
from slack.web.classes.objects import MarkdownTextObject
from slack.web.classes.elements import ButtonElement, ImageElement
from slack.web.classes.messages import Message

pp = PrettyPrinter(indent=4)

def header_builder(title: str) -> SectionBlock:
    fields: List[MarkdownTextObject] = []
    fields.append(MarkdownTextObject(text=f"*{title}*"))
    return SectionBlock(fields=fields)

def details_builder(project: str, project_url:str, user: str, ref: str, issue_id: str, issue_url: str, run_id: str, run_url: str) -> SectionBlock:
    fields: List[MarkdownTextObject] = []
    fields.append(MarkdownTextObject(text=f"*Project Repo:*\n<{project_url}|{project}>"))
    fields.append(MarkdownTextObject(text=f"*Issue ID:*\n<{issue_url}|#{issue_id}>"))
    fields.append(MarkdownTextObject(text=f"*Workflow:*\n<{run_url}|{run_id}>"))
    fields.append(MarkdownTextObject(text=f"*Ref:*\n{ref}"))
    fields.append(MarkdownTextObject(text=f"*From:*\n{user}"))
    image_element: ImageElement = ImageElement(image_url="https://avatars0.githubusercontent.com/u/44036562", alt_text="GitHub Worflow")
    return SectionBlock(fields=fields, accessory=image_element)

def status_builder(build_status: Optional[str] = None, test_status: Optional[str] = None, deploy_status: Optional[str] = None) -> SectionBlock:
    fields: List[MarkdownTextObject] = []
    text: str = ""
    if build_status:
        text += "*Build*: "
        text += ":heavy_check_mark:\n" if build_status == "PASS" else ":x:\n"
    if test_status:
        text += "*Tests*: "
        text += ":heavy_check_mark:\n" if test_status == "PASS" else ":x:\n"
    if deploy_status:
        text += "*Deploy*: "
        text += ":heavy_check_mark:\n" if deploy_status == "PASS" else ":x:\n"
    fields.append(MarkdownTextObject(text=text))
    return SectionBlock(fields=fields)

def message_builder(title: str, blocks: List[Union[ActionsBlock, SectionBlock]]) -> Message:
    return Message(text=f"{title}", blocks=blocks)

def buttons_builder(message_type: str, repository: str, ref: str, run_id: str, workflow: Optional[str] = None) -> ActionsBlock:
    elements: List[ButtonElement] = []
    if message_type == "ERROR":
        retry_value: Dict = { "url_call": f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/rerun" }
        elements.append(ButtonElement(text="Retry", action_id="retry", value=dumps(retry_value)))
    elif message_type == "REQUEST":
        approve_payload: Dict = { "ref": ref, "inputs": { "is_approved": "1" } }
        approve_value: Dict = { "url_call": f"https://api.github.com/repos/{repository}/actions/workflows/{workflow}/dispatches", "payload": dumps(approve_payload)}
        elements.append(ButtonElement(text="Approve", action_id="approval", value=dumps(approve_value), style="primary"))
        deny_payload: Dict = { "ref": ref, "inputs": { "is_approved": "0" } }
        deny_value: Dict = { "url_call": f"https://api.github.com/repos/{repository}/actions/workflows/{workflow}/dispatches", "payload": dumps(deny_payload)}
        elements.append(ButtonElement(text="Deny", action_id="denial", value=dumps(deny_value), style="danger"))
    return ActionsBlock(elements=elements)

def main():
    # Slack API Token
    slack_api_token: str = environ['SLACK_API_TOKEN']
    # Slack Channel name or ID
    slack_channel: str = environ['SLACK_CHANNEL']
    # Optional Slack Message Timestamp
    slack_timestamp: Optional[str] = environ.get('SLACK_TIMESTAMP', None)
    # App or User triggering the action
    user: str = environ['GITHUB_ACTOR']
    # Repository name user/project
    repository: str = environ['GITHUB_REPOSITORY']
    # Optional Workflow file name to manually start
    workflow: Optional[str] = environ.get('WORKFLOW', None)
    # Optional Workflow ID to re-run
    run_id: str = environ['GITHUB_RUN_ID']
    # Workflow url for re-run
    run_url: str = f"https://github.com/{repository}/actions/runs/{run_id}"
    # Branch ref
    ref: str = environ.get('GITHUB_REF', "")
    # Message type, "ERROR" or "REQUEST"
    message_type: Optional[str] = environ.get('MESSAGE_TYPE', None)
    # Message title
    title: str = environ['TITLE']
    # Project name
    project: str = environ['PROJECT_NAME']
    # GitHub project URL
    project_url: str = f"{environ['GITHUB_SERVER_URL']}/{repository}/tree/{ref}"
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

    blocks: List[Union[ActionsBlock,SectionBlock]] = []

    # Build header title section
    blocks.append(header_builder(title=title))
    # Build project information section
    blocks.append(details_builder(project=project, project_url=project_url, user=user, ref=ref, issue_id=issue_id, issue_url=issue_url, run_id=run_id, run_url=run_url))
    # Build workflow information section
    blocks.append(status_builder(build_status=build_status, test_status=test_status, deploy_status=deploy_status))
    # Build interactive section if needed
    if message_type in ['ERROR', 'REQUEST']:
        blocks.append(buttons_builder(message_type=message_type, repository=repository, ref=ref, run_id=run_id, workflow=workflow))
    # Build message
    message: Dict = message_builder(title=title, blocks=blocks).to_dict()
    # Sending message
    client: WebClient = WebClient(token=slack_api_token)
    if slack_timestamp:
        # Will alterate last Slack Message
        print(f"{slack_channel}, {slack_timestamp}")
        try:
            client.chat_update(channel=slack_channel, ts=slack_timestamp, **message)
        except SlackApiError:
            client.chat_postMessage(channel=slack_channel, **message)
    else:
        # Will send new Slack Message
        client.chat_postMessage(channel=slack_channel, **message)

if __name__ == "__main__":
    main()
