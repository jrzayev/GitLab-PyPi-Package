
# GitLab PyPI Package Management Script

This Python script allows you to manage PyPI packages in GitLab by performing various actions, including cloning packages between projects, generating a CSV of package information, retrieving package details, and deleting packages from a project.

## Features

- **SSO Authentication**: Authenticate using GitLab SSO and automatically retrieve the GitLab token and username.
- **Package Cloning**: Clone all PyPI packages from a source GitLab project to a destination project.
- **CSV Generation**: Generate a CSV file that lists all unique PyPI package names and versions from a specified project.
- **Package Information**: Retrieve and display detailed information about a specific package from a project.
- **Package Deletion**: Delete all PyPI packages from a specified GitLab project.

## Requirements

Before running the script, make sure you have the following installed:
- Python 3.x
- Required Python packages:
  - `requests`
  - `csv`
  - `lxml`
  - `twine`

You can install the required packages using pip:
```bash
pip install requests lxml twine
```

## Setup

1. **Clone the repository or download the script** to your local machine.
2. **Install the required packages** by running:
   ```bash
   pip install requests lxml twine
   ```
3. **SSO Authentication Setup**:
   Set up the following environment variables for SSO authentication:
   - `GITLAB_CLIENT_ID`: The client ID of your GitLab OAuth application.
   - `GITLAB_CLIENT_SECRET`: The client secret of your GitLab OAuth application.

   These values can be obtained from your GitLab instance by registering your application in the **GitLab Application Settings**.

4. **Run the script** using the commands below, depending on the action you want to perform.

## Command-Line Arguments

| Argument            | Description                                                                                  |
|---------------------|----------------------------------------------------------------------------------------------|
| `action`            | The action to perform. Choices are: `package_info`, `clone`, `get_csv`, `delete`.            |
| `--gitlab_server`   | GitLab server URL. This is required for all actions.                                         |
| `--gitlab_token`    | GitLab private token (optional if SSO is used).                                              |
| `--gitlab_username` | GitLab username (optional if SSO is used or required for cloning).                           |
| `--src_project_id`  | Source GitLab project ID (required for cloning).                                             |
| `--dst_project_id`  | Destination GitLab project ID (required for cloning).                                        |
| `--project_id`      | GitLab project ID (required for CSV generation, package info, or deletion).                  |
| `--package_id`      | Package ID for retrieving specific package information (required for `package_info` action). |
| `--sso`             | Use SSO authentication to obtain GitLab token and username.                                  |

## SSO Authentication Details

The `sso_authenticate` function uses OAuth2 for authentication. It opens a browser to the GitLab SSO login page, requests the user's authorization, and then exchanges the authorization code for an access token.

**Required Environment Variables**:
- `GITLAB_CLIENT_ID`: Your GitLab OAuth application’s client ID.
- `GITLAB_CLIENT_SECRET`: Your GitLab OAuth application’s client secret.

You must first register your application in GitLab to obtain these values. Go to **Settings > Applications** in your GitLab instance and create a new OAuth application.

The script will open a URL in your browser where you log in and authorize the application. You’ll then be redirected to the `REDIRECT_URI` (default: `http://localhost:8000/callback`) with an authorization code, which the script will exchange for an access token.

## Example Usages

### 1. `clone`
Clones all PyPI packages from the source GitLab project to the destination GitLab project.

**Required Arguments**:
- `--gitlab_server`
- `--gitlab_token` or `--sso`
- `--gitlab_username` (if SSO is not used)
- `--src_project_id`
- `--dst_project_id`

**Example Usage**:
```bash
python script.py clone --gitlab_server "https://gitlab.example.com" --gitlab_token "your_token" --gitlab_username "your_username" --src_project_id "123" --dst_project_id "456"
```

With SSO:
```bash
python script.py clone --gitlab_server "https://gitlab.example.com" --sso --src_project_id "123" --dst_project_id "456"
```

### 2. `get_csv`
Generates a CSV file (`get-uniq-pypi-package-name-and-version.csv`) with unique package names and versions from the specified GitLab project.

**Required Arguments**:
- `--gitlab_server`
- `--gitlab_token` or `--sso`
- `--project_id`

**Example Usage**:
```bash
python script.py get_csv --gitlab_server "https://gitlab.example.com" --gitlab_token "your_token" --project_id "123"
```

With SSO:
```bash
python script.py get_csv --gitlab_server "https://gitlab.example.com" --sso --project_id "123"
```

### 3. `package_info`
Retrieves and displays information about a specific PyPI package in a project.

**Required Arguments**:
- `--gitlab_server`
- `--gitlab_token` or `--sso`
- `--project_id`
- `--package_id`

**Example Usage**:
```bash
python script.py package_info --gitlab_server "https://gitlab.example.com" --gitlab_token "your_token" --project_id "123" --package_id "456"
```

With SSO:
```bash
python script.py package_info --gitlab_server "https://gitlab.example.com" --sso --project_id "123" --package_id "456"
```

### 4. `delete`
Deletes all PyPI packages from the specified GitLab project.

**Required Arguments**:
- `--gitlab_server`
- `--gitlab_token` or `--sso`
- `--project_id`

**Example Usage**:
```bash
python script.py delete --gitlab_server "https://gitlab.example.com" --gitlab_token "your_token" --project_id "123"
```

With SSO:
```bash
python script.py delete --gitlab_server "https://gitlab.example.com" --sso --project_id "123"
```

## Authentication via SSO

If you want to authenticate via GitLab's Single Sign-On (SSO), you can pass the `--sso` flag. When using SSO, you do not need to provide `--gitlab_token` or `--gitlab_username`, as these will be retrieved automatically via OAuth2 authentication.

**Example Usage**:
```bash
python script.py clone --gitlab_server "https://gitlab.example.com" --sso --src_project_id "123" --dst_project_id "456"
```

## Tested Python Versions

This script has been tested and works with the following Python versions:

- Python 3.10
- Python 3.11
- Python 3.12

Make sure you are using one of these versions for compatibility.


## Error Handling

- If required arguments for a specific action are missing, the script will display an error message and exit.
- Ensure that the GitLab token or SSO authentication is valid to avoid authentication failures.

## License

This project is open source and licensed under the [MIT License](LICENSE).
