from fastapi.responses import HTMLResponse
from aiofiles import open as aopen

TEMPLATE_PATH = "./templates/exceptions.html"

class HTTPExceptionLoading:
    def __init__(self):
        self.template = ""

    async def _load_template(self):
        async with aopen(TEMPLATE_PATH, "r") as f:
            self.template = await f.read()

    async def _render(self, code: str, hint: str = "") -> HTMLResponse:
        await self._load_template()
        html = (
            self.template
            .replace("$EXCEPTION_CODE", code)
            .replace("$EXCEPTION_HINT", hint)
        )
        return HTMLResponse(html)

    async def error_403(self) -> HTMLResponse:
        return await self._render("403 ACCESS DENIED")

    async def error_404(self) -> HTMLResponse:
        return await self._render("404 NOT FOUND")

    async def error_405(self) -> HTMLResponse:
        return await self._render("405 METHOD NOT ALLOWED")

    async def error_500(self) -> HTMLResponse:
        return await self._render("500 INTERNAL SERVER ERROR")
