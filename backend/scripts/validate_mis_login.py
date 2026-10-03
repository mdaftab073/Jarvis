"""Interactively verify SVNIT MIS login and all supported HTML parsers."""

import argparse
import base64
import getpass
import json
import os
import sys
import tempfile
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_ROOT.parent / ".env", override=False)
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.mis import MISClient, MISParser  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-bootstrap",
        action="store_true",
        help="fetch the login page and verify hidden fields, RSA keys, and captcha without logging in",
    )
    args = parser.parse_args()

    base_url = os.environ.get("SVNIT_MIS_BASE_URL", "").strip()
    if not base_url:
        raise SystemExit(
            "Set SVNIT_MIS_BASE_URL to the HTTPS MIS host origin, "
            "for example https://mis.svnit.ac.in."
        )
    parsed_url = urlparse(base_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise SystemExit("SVNIT_MIS_BASE_URL must use HTTPS and include a host.")
    if parsed_url.username or parsed_url.password:
        raise SystemExit("SVNIT_MIS_BASE_URL must not contain credentials.")
    if parsed_url.path not in {"", "/"} or parsed_url.query or parsed_url.fragment:
        raise SystemExit(
            "SVNIT_MIS_BASE_URL must be the HTTPS host origin; set the page path "
            "in SVNIT_MIS_CONFIGURATION_JSON."
        )
    try:
        configuration = json.loads(os.environ.get("SVNIT_MIS_CONFIGURATION_JSON", "{}"))
    except json.JSONDecodeError as error:
        raise SystemExit("SVNIT_MIS_CONFIGURATION_JSON must contain valid JSON.") from error
    if not isinstance(configuration, dict):
        raise SystemExit("SVNIT_MIS_CONFIGURATION_JSON must be a JSON object.")

    client = MISClient(base_url, configuration)
    try:
        login_page = client.fetch_login_page()
        html = client._auth._login_html or ""
        hidden_fields = client._auth.extract_hidden_fields(html)
        rsa_keys = client._auth.extract_rsa_keys(html)
        if not hidden_fields:
            raise SystemExit("Login page did not expose ASP.NET hidden form fields.")
        if "__VIEWSTATE" not in hidden_fields:
            raise SystemExit("Login page did not expose the ASP.NET __VIEWSTATE field.")
        if not rsa_keys["modulus"] or not rsa_keys["exponent"]:
            raise SystemExit("Login page did not expose both RSA public key fields.")
        print(f"PASS login page and hidden fields fetched ({len(hidden_fields)} fields)")
        client.build_rsa_key(rsa_keys["modulus"], rsa_keys["exponent"])
        print("PASS RSA public key constructed")
        if args.check_bootstrap:
            if not login_page.captcha_image:
                raise SystemExit("Login page did not return a captcha image payload.")
            print("PASS captcha image fetched and encoded")
            return

        if login_page.captcha_image:
            image_type, encoded = login_page.captcha_image.split(",", 1)
            suffix = ".jpg" if "jpeg" in image_type else ".png"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as image_file:
                image_file.write(base64.b64decode(encoded))
                image_path = Path(image_file.name)
            try:
                webbrowser.open(image_path.as_uri())
                print("A browser tab has opened the MIS captcha image.")
                captcha = input("Enter the captcha shown by MIS: ").strip()
            finally:
                image_path.unlink(missing_ok=True)
        else:
            captcha = input("Enter the MIS captcha (if required): ").strip()

        username = os.environ.get("SVNIT_MIS_USERNAME") or input("MIS username: ").strip()
        password = os.environ.get("SVNIT_MIS_PASSWORD") or getpass.getpass("MIS password: ")
        client.login({"username": username, "password": password, "captcha": captcha})
        print("PASS session login")
        parser = MISParser()
        checks = (
            ("profile", client.fetch_student_profile, parser.parse_student_profile),
            ("attendance", client.fetch_attendance, parser.parse_attendance),
            ("results", client.fetch_results, parser.parse_results),
            ("timetable", client.fetch_timetable, parser.parse_timetable),
        )
        for name, fetch, parse in checks:
            parsed = parse(fetch())
            print(f"PASS {name} parsing ({len(parsed.model_dump().get('records', parsed.model_dump().get('entries', [])))} rows)")
    finally:
        client.close()


if __name__ == "__main__":
    main()
