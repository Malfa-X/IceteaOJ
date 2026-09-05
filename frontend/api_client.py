from dataclasses import dataclass

import requests


@dataclass
class ApiResult:
    ok: bool
    status_code: int
    msg: str
    data: object | None


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def get(self, path: str, params: dict | None = None) -> ApiResult:
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict | None = None) -> ApiResult:
        return self._request("POST", path, json=json)

    def put(self, path: str, json: dict | None = None) -> ApiResult:
        return self._request("PUT", path, json=json)

    def delete(self, path: str) -> ApiResult:
        return self._request("DELETE", path)

    def _request(self, method: str, path: str, **kwargs) -> ApiResult:
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                timeout=10,
                **kwargs,
            )
            payload = response.json()
            return ApiResult(
                ok=response.ok,
                status_code=response.status_code,
                msg=payload.get("msg", ""),
                data=payload.get("data"),
            )
        except requests.RequestException as error:
            return ApiResult(
                ok=False,
                status_code=0,
                msg=f"request failed: {error}",
                data=None,
            )
        except ValueError:
            return ApiResult(
                ok=False,
                status_code=response.status_code,
                msg="invalid json response",
                data=None,
            )