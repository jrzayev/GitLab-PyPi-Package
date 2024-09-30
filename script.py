import argparse
import requests
import csv
import re
import os
import twine.commands.upload
import twine.settings
import webbrowser
from lxml import html
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading


CLIENT_ID = os.getenv("GITLAB_CLIENT_ID", None)
CLIENT_SECRET = os.getenv("GITLAB_CLIENT_SECRET", None)
REDIRECT_URI = "http://localhost:8000/callback"
GITLAB_AUTH_URL = "/oauth/authorize"
GITLAB_TOKEN_URL = "/oauth/token"
GITLAB_API_URL = "/api/v4/user"

auth_code = None


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = urlparse(self.path).query
        params = parse_qs(query)

        if 'code' in params:
            auth_code = params['code'][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"Authorization successful. You can close this tab.")
        else:
            self.send_response(400)
            self.end_headers()


def run_callback_server():
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, OAuthCallbackHandler)
    httpd.handle_request()


def get_gitlab_oauth_url(gitlab_server):
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "read_user api"
    }
    return f"{gitlab_server}{GITLAB_AUTH_URL}?" + urlencode(params)


def sso_authenticate(gitlab_server):
    if CLIENT_ID is None or CLIENT_SECRET is None:
        return None, None
    global auth_code
    auth_code = None

    server_thread = threading.Thread(target=run_callback_server)
    server_thread.daemon = True
    server_thread.start()

    oauth_url = get_gitlab_oauth_url(gitlab_server)
    print(f"Please go to the following URL to authenticate:\n{oauth_url}")

    webbrowser.open(oauth_url)

    server_thread.join()

    if auth_code:
        token_response = requests.post(f"{gitlab_server}{GITLAB_TOKEN_URL}", data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI
        })

        if token_response.status_code == 200:
            access_token = token_response.json()["access_token"]

            headers = {"Authorization": f"Bearer {access_token}"}
            user_response = requests.get(f"{gitlab_server}{GITLAB_API_URL}", headers=headers)

            if user_response.status_code == 200:
                gitlab_user = user_response.json()["username"]
                print(f"Authenticated as {gitlab_user}")
                return access_token, gitlab_user
            else:
                print("Failed to fetch user information")
        else:
            print("Failed to authenticate with GitLab")
    else:
        print("Failed to capture authorization code")

    return None, None


def get_pypi_package_info(gitlab_server, gitlab_token, project_id, package_id):
    gitlab_api_server = f"{gitlab_server}/api/v4"
    headers = {'PRIVATE-TOKEN': gitlab_token}
    api_endpoint = f"{gitlab_api_server}/projects/{project_id}/packages/{package_id}"
    response = requests.get(url=api_endpoint, headers=headers)
    package_info = response.json()
    print(f"Package Information for ID {package_id}:\n{package_info}")
    return package_info


def get_pypi_project_x_total_pages(gitlab_server, gitlab_token, project_id):
    gitlab_api_server = f"{gitlab_server}/api/v4"
    headers = {'PRIVATE-TOKEN': gitlab_token}
    api_endpoint = f"{gitlab_api_server}/projects/{project_id}/packages?per_page=100"
    response = requests.get(url=api_endpoint, headers=headers)
    return response.headers['X-Total-Pages']


def get_pypi_project_id_list(gitlab_server, gitlab_token, project_id):
    gitlab_api_server = f"{gitlab_server}/api/v4"
    headers = {'PRIVATE-TOKEN': gitlab_token}
    x_total_pages = int(get_pypi_project_x_total_pages(gitlab_server, gitlab_token, project_id)) + 1
    package_ids = []
    for i in range(1, x_total_pages):
        api_endpoint = f"{gitlab_api_server}/projects/{project_id}/packages?per_page=100&page={i}"
        response = requests.get(url=api_endpoint, headers=headers)
        for package_id in response.json():
            package_ids.append(package_id['id'])
    return package_ids


def get_uniq_pypi_package_name_and_version_csv(gitlab_server, gitlab_token, project_id):
    open('get-uniq-pypi-package-name-and-version.csv', 'w').close()
    for package_id in get_pypi_project_id_list(gitlab_server, gitlab_token, project_id):
        package_info = get_pypi_package_info(gitlab_server, gitlab_token, project_id, package_id)
        with open('get-uniq-pypi-package-name-and-version.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([package_info['name'], package_info['version']])


def clone_all_pypi_packages_from_src_to_dst(gitlab_user, gitlab_token, gitlab_server, src_project_id,
                                            dst_project_id):
    gitlab_api_server = f"{gitlab_server}/api/v4"
    headers = {'PRIVATE-TOKEN': gitlab_token}
    temporary_cache = []
    twine_api_endpoint = f"{gitlab_api_server}/projects/{dst_project_id}/packages/pypi"
    os.environ["TWINE_USERNAME"] = gitlab_user
    os.environ["TWINE_PASSWORD"] = gitlab_token
    for package_id in get_pypi_project_id_list(gitlab_server, gitlab_token, src_project_id):
        package_info = get_pypi_package_info(gitlab_server, gitlab_token, src_project_id, package_id)
        package_name = package_info['name']
        html_endpoint = f"{gitlab_api_server}/projects/{src_project_id}/packages/pypi/simple/{package_name}"
        page = requests.get(url=html_endpoint, headers=headers)
        webpage = html.fromstring(page.content).xpath('//a/@href')

        for url in webpage:
            response = requests.get(url, stream=True, headers=headers)
            file_name = re.findall("filename=\"(.+)\"", response.headers['content-disposition'])[0]

            if file_name not in temporary_cache:
                temporary_cache.append(file_name)
                with open(file_name, 'wb') as file:
                    file.write(response.raw.read())
                try:
                    twine.commands.upload.main(['--repository-url', twine_api_endpoint, file_name, '--verbose'])
                except:
                    print("File exists")
                os.remove(file_name)


def delete_all_pypi_packages(gitlab_server, gitlab_token, project_id):
    gitlab_api_server = f"{gitlab_server}/api/v4"
    confirmation = input(f"Are you sure you want to delete all PyPI packages from project {project_id}? Type 'yes' to confirm: ")
    if confirmation.lower() == 'yes':
        headers = {'PRIVATE-TOKEN': gitlab_token}
        package_ids = get_pypi_project_id_list(gitlab_server, gitlab_token, project_id)
        if not package_ids:
            print("No packages found to delete.")
            return
        for package_id in package_ids:
            api_endpoint = f"{gitlab_server}/projects/{project_id}/packages/{package_id}"
            response = requests.delete(url=api_endpoint, headers=headers)
    else:
        print("Deletion cancelled.")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage PyPI packages in GitLab using SSO authentication or GitLab token.",
        formatter_class=argparse.RawTextHelpFormatter  # Preserve formatting in help text
    )

    parser.add_argument(
        "action",
        choices=["package_info", "clone", "get_csv", "delete"],
        help=(
            "- package_info: Get information about a specific PyPI package.\n"
            "- clone: Clone all PyPI packages from the source GitLab project to the destination project.\n"
            "- get_csv: Generate a CSV with unique PyPI package names and versions from the specified project.\n"
            "- delete: Delete all PyPI packages from the specified project."
        )
    )

    parser.add_argument("--gitlab_server", required=True, help="GitLab server URL")
    parser.add_argument("--gitlab_token", required=False, help="GitLab private token (ignored if SSO is used)")
    parser.add_argument("--gitlab_user", required=False, help="GitLab username (can be obtained via SSO)")
    parser.add_argument("--src_project_id", required=False, help="Source GitLab project ID (required for cloning)")
    parser.add_argument("--dst_project_id", required=False, help="Destination GitLab project ID (required for cloning)")
    parser.add_argument("--project_id", required=False,
                        help="GitLab project ID for CSV generation, deletion, or package info")
    parser.add_argument("--package_id", required=False,
                        help="Package ID for retrieving package information (required for package_info action)")
    parser.add_argument("--sso", action="store_true", help="Use SSO authentication to obtain GitLab token and username")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.sso:
        gitlab_token, gitlab_user = sso_authenticate(args.gitlab_server)
        if gitlab_user is None or gitlab_token is None:
            print("There is a problem with SSO authentication")
            exit(1)
        print(f"Authenticated with SSO, using token: {gitlab_token} and username: {gitlab_user}")
    else:
        gitlab_token = args.gitlab_token
        gitlab_user = args.gitlab_user
        if not gitlab_token:
            print("GitLab token is required if SSO is not used.")
            exit(1)
        elif not gitlab_user and args.action == "clone":
            print("GitLab username is required for cloning if SSO is not used.")
            exit(1)

    if args.action == "package_info":
        if not args.project_id or not args.package_id:
            print("Project ID and Package ID are required to return package information.")
            exit(1)
        else:
            get_pypi_package_info(args.gitlab_server, gitlab_token, args.project_id, args.package_id)

    elif args.action == "clone":
        if not args.src_project_id or not args.dst_project_id:
            print("Source project ID and Destination project ID are required for cloning.")
            exit(1)
        else:
            clone_all_pypi_packages_from_src_to_dst(gitlab_user, gitlab_token,
                                                    args.gitlab_server, args.src_project_id,
                                                    args.dst_project_id)

    elif args.action == "get_csv":
        if not args.project_id:
            print("Project ID is required for generating CSV.")
            exit(1)
        else:
            get_uniq_pypi_package_name_and_version_csv(args.gitlab_server, gitlab_token, args.project_id)

    elif args.action == "delete":
        if not args.project_id:
            print("Project ID is required for deletion.")
            exit(1)
        else:
            delete_all_pypi_packages(args.gitlab_server, gitlab_token, args.project_id)
