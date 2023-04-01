from lsprotocol.types import (
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionParams,
    MessageType,
    Command,
    Range,
    Position,
    TextDocumentEdit,
    WorkspaceEdit,
    OptionalVersionedTextDocumentIdentifier,
    TextEdit,
)

from pygls.server import LanguageServer
from pygls.workspace import Document, Workspace
import openai
import os

openai.api_key = os.getenv("OPENAI_KEY")


def _fix_syntax_and_grammar(text):
    return openai.Edit.create(
        model="text-davinci-edit-001",
        input=text,
        instruction="Fix the grammar and spelling mistakes",
        temperature=0.7,
        top_p=1,
    )["choices"][0]["text"]


def _edit_doc(doc, range, new_text):
    return TextDocumentEdit(
        text_document=OptionalVersionedTextDocumentIdentifier(
            uri=doc.uri, version=doc.version
        ),
        edits=[TextEdit(range, new_text)],
    )


class Server(LanguageServer):
    current_doc_uri: str = None

    def get_current_doc(self) -> Document:
        return self.workspace.get_document(self.current_doc_uri)


server = Server("Lovelaice", "v0.1")


@server.feature(TEXT_DOCUMENT_CODE_ACTION)
def on_code_action(ls: Server, params: CodeActionParams):
    uri = params.text_document.uri
    range = params.range

    return [Command("Fix grammar and spelling", "fixSyntaxAndGrammar", (uri, range))]


@server.thread()
@server.command("fixSyntaxAndGrammar")
def fix_syntax_and_grammar(ls: Server, args):
    uri, range = args
    range = Range(start=Position(**range["start"]), end=Position(**range["end"]))

    doc: Document = ls.workspace.get_document(uri)
    start = doc.offset_at_position(range.start)
    end = doc.offset_at_position(range.end)

    if abs(start - end) <= 3:
        ls.show_message("Select a larger fragment of text.", MessageType.Error)
        return

    text = doc.source[start:end]
    fix = _fix_syntax_and_grammar(text)

    ls.apply_edit(WorkspaceEdit(document_changes=[_edit_doc(doc, range, fix)]))
    ls.show_message("Replaced %i characters" % len(text))
