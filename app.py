import os
import asyncio
from uuid import uuid4
from typing import List
from nicegui import ui, events
import httpx
from dotenv import load_dotenv
load_dotenv()

API_BASE = os.getenv('FASTAPI_API_BASE')

class ChatMessage:
    def __init__(self, role: str, content: str, tokens: int = 0) -> None:
        self.role = role
        self.content = content
        self.tokens = tokens

class DocumentQA:
    def __init__(self):
        self.history: List[ChatMessage] = []
        self.is_processing = False
        self.uploaded_files_ui = None
        self.session_id = str(uuid4())

    async def render_uploaded_files(self):
        if self.uploaded_files_ui is None:
            return
        self.uploaded_files_ui.clear()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{API_BASE}/files")
                files = resp.json()["files"]
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            # Backend not ready yet, show empty state
            with self.uploaded_files_ui:
                ui.label("Backend connecting...") \
                    .classes("text-xs text-gray-400")
            return
        except Exception as e:
            # Other errors, show message
            with self.uploaded_files_ui:
                ui.label(f"Error loading files: {str(e)}") \
                    .classes("text-xs text-red-400")
            return

        with self.uploaded_files_ui:
            if not files:
                ui.label("No documents uploaded yet.") \
                    .classes("text-xs text-gray-400")
                return

            for f in files:
                with ui.card().classes(
                    "w-full p-2 flex flex-col gap-1 bg-white shadow-sm border border-slate-200 rounded-x"
                ):
                    with ui.row().classes("items-center justify-between"):
                        ui.label(f"📄 {f['file_name']}") \
                            .classes("text-sm font-medium")
                        ui.button(
                            icon="delete",
                            color="negative",
                            on_click=lambda f=f:
                                self.on_delete_clicked(
                                    document_id=f["namespace"],
                                    file_name=f["file_name"],
                                ),
                        ).props("flat round dense")

    async def handle_upload(self, e: events.UploadEventArguments):
        """Handle PDF upload, I must. Timeout long, make it I will."""
        filename = e.file.name

        ui.notify(f"Uploading {filename}…", type="info")
        status_label.set_text("Parsing PDF…")
        status_indicator.set_visibility(True)

        try:
            # Long timeout for PDF processing and Pinecone indexing
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{API_BASE}/upload/pdf",
                    files={"file": (filename, e.file._data, "application/pdf")},
                )

            status_indicator.set_visibility(False)

            if resp.status_code != 200:
                status_label.set_text(f"Failed: {filename}")
                error_msg = resp.json().get("detail", "PDF indexing failed") if resp.status_code != 200 else "Unknown error"
                ui.notify(f"Upload failed: {error_msg}", type="negative")
                return

            status_label.set_text(f"Ready: {filename}")
            ui.notify("PDF indexing complete", type="positive", icon="check")

            await self.render_uploaded_files()
        except httpx.TimeoutException:
            status_indicator.set_visibility(False)
            status_label.set_text(f"Timeout: {filename}")
            ui.notify("Upload timed out. File may be processing. Please check later.", type="warning")
        except Exception as ex:
            status_indicator.set_visibility(False)
            status_label.set_text(f"Error: {filename}")
            ui.notify(f"Upload error: {str(ex)}", type="negative")

    def on_delete_clicked(self, document_id: str, file_name: str):
        async def task():
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{API_BASE}/files/{document_id}",
                    params={"file_name": file_name},
                )

            with self.uploaded_files_container:
                if resp.status_code == 200:
                    ui.notify(f"{file_name} deleted 🗑️", type="positive")
                    asyncio.create_task(self.render_uploaded_files())
                else:
                    ui.notify(
                        resp.json().get("detail", "Delete failed"),
                        type="negative",
                    )

        asyncio.create_task(task())

    async def stream_chat(self, prompt: str, dom_id: str):
        js = f"""
        (() => {{
            (async () => {{
                try {{
                    const response = await fetch('{API_BASE}/chat/stream', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json'
                        }},
                        body: JSON.stringify({{
                            q: {repr(prompt)},
                            session_id: {repr(self.session_id)}
                        }})
                    }});

                    if (!response.body) return;

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    let fullText = '';
                    let exploring = false;
                    let jigInterval = null;

                    const el = document.getElementById('{dom_id}');
                    if (!el) return;

                    function startJigJag() {{
                        let dots = 0;
                        jigInterval = setInterval(() => {{
                            dots = (dots + 1) % 4;
                            const zig = '...'.slice(0, dots + 1);
                            el.innerText = 'Exploring ' + zig;
                        }}, 250);
                    }}

                    function stopJigJag() {{
                        if (jigInterval) {{
                            clearInterval(jigInterval);
                            jigInterval = null;
                        }}
                    }}

                    while (true) {{
                        const {{ value, done }} = await reader.read();
                        if (done) break;

                        const chunk = decoder.decode(value, {{ stream: true }});

                        // Detect tool-call chunk
                        if (chunk.includes('< Exploring >')) {{
                            if (!exploring) {{
                                exploring = true;
                                startJigJag();
                            }}
                            continue;
                        }}

                        // First real response chunk
                        if (exploring) {{
                            stopJigJag();
                            exploring = false;
                            el.innerText = '';
                        }}

                        fullText += chunk;
                        el.innerHTML = marked.parse(fullText);
                    }}

                    stopJigJag();

                }} catch (error) {{
                    const el = document.getElementById('{dom_id}');
                    if (el) el.innerText = 'Error: ' + error.message;
                }}
            }})();
            return 'started';
        }})();
        """

        ui.run_javascript(js)

    async def send_message(self):
        """Send message, display it I must. Assistant response, style it I will."""
        prompt = user_input.value.strip()
        if not prompt or self.is_processing:
            return

        self.is_processing = True
        user_input.value = ""
        # Unique ID for this message,
        message_id = f"msg-{uuid4().hex[:8]}"
        assistant_dom_id = f"assistant-{message_id}"
        response_label = None
        spinner = None
        with chat_container:
            with ui.column().classes('w-full items-end gap-0 mb-2'):
                ui.label('You').classes('text-blue-500 text-xs mr-1 uppercase font-black tracking-tighter')
                ui.markdown(prompt).classes(
                    'bg-slate-100 px-3 py-1.5 rounded-2xl rounded-tr-none text-slate-800 max-w-[85%] border border-slate-200'
                )

            with ui.row().classes("w-full items-start mb-4"):
                with ui.column().classes("bg-blue-50 p-4 rounded-2xl rounded-tl-none border border-blue-100 text-slate-800 max-w-[80%]"):
                    ui.label("Assistant").classes("text-xs text-blue-500 ml-2 mb-1 uppercase font-bold")
                    response_label = ui.label("").props(f"id={assistant_dom_id}") \
                        .classes("text-gray-800 whitespace-pre-wrap break-words")
                    spinner = ui.spinner(size="sm", color="blue") \
                        .classes("mt-2")
                    spinner.set_visibility(True)

        try:
            await self.stream_chat(prompt, assistant_dom_id)
            await asyncio.sleep(0.5)
        except Exception as e:
            # Error handling
            if response_label:
                response_label.set_text(f"Error: {str(e)}")
            ui.notify(f"Chat error: {str(e)}", type="negative")
        finally:
            # Spinner, hide it
            if spinner:
                spinner.set_visibility(False)
            self.is_processing = False

app_logic = DocumentQA()
ui.query("body").style("background-color: #f8fafc;")
ui.add_head_html("""
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        """)

with ui.header(elevated=True).classes(
    "bg-slate-800 text-white p-4 justify-between items-center"
):
    with ui.row().classes("items-center gap-4"):
        ui.icon("description", size="md")
        ui.label("TacticalEdge RAG-Chat") \
            .classes("text-xl font-bold tracking-tight")

    with ui.row().classes("items-center gap-2"):
        status_indicator = ui.spinner(size="sm", color="white")
        status_indicator.set_visibility(False)
        status_label = ui.label("System Ready") \
            .classes("text-xs opacity-80")


with ui.left_drawer(fixed=False).classes(
    "bg-slate-50 border-r p-6"
).props("width=320"):
    ui.label("Knowledge Base") \
        .classes("text-sm font-bold text-slate-500 uppercase mb-4")

    with ui.card().classes(
        "w-full border-dashed border-2 bg-transparent p-4 items-center text-center"
    ):
        ui.upload(
            label="Upload PDF Source",
            on_upload=lambda e: app_logic.handle_upload(e),
            auto_upload=True,
        ).props(
            "flat bordered color=primary accept=.pdf"
        ).classes("w-full")

    ui.markdown("---")

    ui.label("Uploaded Documents") \
        .classes("text-xs font-bold text-slate-400 mb-2")

    app_logic.uploaded_files_container = ui.column().classes('gap-2')
    app_logic.uploaded_files_ui = app_logic.uploaded_files_container
    # Wait a bit before first API call to ensure backend is ready
    ui.timer(
        2.0,
        lambda: asyncio.create_task(app_logic.render_uploaded_files()),
        once=True,
    )

with ui.column().classes(
    "w-full max-w-4xl mx-auto p-4 mb-32 gap-4"
):
    chat_container = ui.column().classes("w-full gap-4")


with ui.footer().classes("bg-transparent p-6"):
    with ui.row().classes(
        "w-full max-w-4xl mx-auto bg-white rounded-2xl shadow-lg border p-2 items-center"
    ):
        user_input = (
            ui.input(placeholder="Ask about your document…")
            .classes("flex-grow pl-4 border-none")
            .props("borderless")
            .on("keydown.enter", lambda: app_logic.send_message())
        )

        ui.button(
            icon="send",
            on_click=lambda: app_logic.send_message(),
        ).props("round flat color=primary")

ui.run(title="TacticalEdge AI - RAG Chat")
