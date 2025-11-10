# Preview:  Core Content Services MCP Server

## Overview

The Core Content Services MCP Server provides a standardized interface that enables IBM FileNet Content Manager (FNCM) capabilities to be used by AI models.  This MCP Server enables you to:

- Manage documents stored within FNCM through AI Agents, including document creation and deletion
- Perform updates to documents such as check in, check out, and property updates
- Search for objects such as documents and folders
- Manage folders and file / un-file documents in folders
- Manage document classes, folder classes, and more

---

## Tools List

The Core Content Services MCP Server provides the following tools for interacting with FileNet CPE:

### Document Management

- **get_document_versions**: Retrieves a document's version history, including major and minor version numbers and document IDs for each version.

- **get_document_text_extract**: Extracts text content from a document by retrieving its text extract annotations. If multiple text extracts are found, they are concatenated. **Note:** This functionality requires the Persistent Text Extract add-on to be installed in your object store. See the [Prerequisites](#prerequisites) section for more details.

- **create_document**: Creates a new document in the content repository with specified properties. Can upload files as the document's content if file paths are provided. Requires first calling determine_class and get_class_property_descriptions.

- **update_document_properties**: Updates an existing document's properties without changing its class. Requires first calling get_class_property_descriptions to get valid properties for the document's current class.

- **update_document_class**: Changes a document's class in the content repository. **WARNING:** Changing a document's class can result in loss of properties if the new class does not have the same properties as the old class. Requires first calling determine_class to get the new class_identifier.

- **checkin_document**: Checks in a document that was previously checked out. Can upload new content files during check-in if file paths are provided.

- **checkout_document**: Checks out a document for editing. Can download the document content to a specified folder path if provided.

- **cancel_document_checkout**: Cancels a document checkout in the content repository, releasing the reservation.

- **get_document_properties**: Retrieves a document from the content repository by ID or path, returning the document object with its properties.

- **get_class_specific_properties_name**: Retrieves a list of class-specific property names for a document based on its class definition. Filters out system properties and hidden properties.

- **delete_document_version**: Deletes a specific document version in the content repository using its document ID.

- **delete_version_series**: Deletes an entire version series (all versions of a document) in the content repository using the version series ID.

### Folder Management

- **create_folder**: Creates a new folder in the content repository with specified name, parent folder, and optional class identifier.

- **delete_folder**: Deletes a folder from the repository using its ID or path.

- **unfile_document**: Removes a document from a folder without deleting the document itself.

- **update_folder**: Updates an existing folder's properties. Requires first calling determine_class and get_class_property_descriptions.

- **get_folder_documents**: Get documents contained in a folder.

### Metadata

- **list_root_classes**: Lists all classes of a specific root class in the repository.

- **list_all_classes**: Lists all classes of a specific root class in the repository.

- **determine_class**: Determines the appropiate class based on the available classes and the content of the user's message or context document.

- **get_class_property_descriptions**: Retrieves detailed descriptions of all properties for a specified class.

### Search

- **get_searchable_property_descriptions**: Retrieves descriptions of properties that can be used in search operations.

- **repository_object_search**: Searches for repository objects based on specified criteria.

- **lookup_documents_by_name**: Searches for documents by matching keywords against document names. Returns a ranked list of matching documents with confidence scores. Useful when you know part of a document's name but not its exact ID or path.

- **lookup_documents_by_path**: Searches for documents based on their location in the folder hierarchy. Matches keywords against folder names and document containment names at each path level. Particularly useful when the user describes a document using path separators (e.g., "/Folder1/Subfolder/document").

### Annotations

- **get_document_annotations**: Retrieves all annotations associated with a document, including their IDs, names, descriptive text, and content elements.

---

## Tested Environments

The Core Content Services MCP Server has been tested with the following MCP client and LLM combinations:
- **Claude Desktop**: Sonnet 4.5, 4, 3.5 and Haiku 4.5
- **Watsonx Orchestrate**: Llama-3-2-90b-vision-instruct

While other MCP client and LLM combinations have not been tested, they may work with this server. We encourage you to experiment and validate for yourself.

For setup instructions with additional MCP clients, see:
- [Bob-IDE MCP Server Setup](/docs/bob-setup.md)
- [VS Code Copilot MCP Server Setup](/docs/vscode-copilot-setup.md)

## MCP Client Limitations

Some MCP clients have limitations that affect which tools can be used. The following table shows known compatibility issues:

| MCP Client | Limitation | Affected Tools |
|------------|------------|----------------|
| Watson Orchestrate | Does not support complex Pydantic classes as input | • `create_document`<br>• `update_document_properties`<br>• `checkout_document`<br>• `checkin_document`<br>• `update_folder`<br>• `repository_object_search` |

> **Note:** These limitations are due to the MCP client's input handling capabilities, not the MCP server itself.

---

## Setup and Configuration

### Prerequisites

- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
  - on macOS: `brew install uv`
  - on Windows: see link above
- Access to a FileNet Content Platform Engine (CPE) server with Content Services GraphQL API (CS-GQL) installed
- **Persistent Text Extract Add-on** must be installed in your object store if you want to use document content retrieval functionality
  - This add-on enables the extraction and storage of text content from documents
  - Without this add-on, the `get_document_text_extract` tool will not return document content
  - For installation instructions, refer to the [IBM Documentation on Installing the Persistent Text Add-on](https://www.ibm.com/docs/en/content-assistant?topic=extraction-installing-persistent-text-add)

### Configuration

The Core Content Services MCP Server requires several environment variables to connect to your FileNet CPE server:

#### Required Environment Variables

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `SERVER_URL` | Content Services GraphQL API endpoint URL (required) | - |
| `USERNAME` | Authentication username (required) | - |
| `PASSWORD` | Authentication password (required) | - |
| `OBJECT_STORE` | Object store identifier (required) | - |

#### Optional Environment Variables

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `SSL_ENABLED` | Whether SSL is enabled. Can be set to `true`, a path to a certificate file, or `false` (not recommended for production) | `true` |
| `TOKEN_SSL_ENABLED` | Whether SSL is enabled for token endpoint. Can be set to `true`, a path to a certificate file, or `false` (not recommended for production) | `true` |
| `TOKEN_REFRESH` | Token refresh interval in seconds | `1800` |
| `TOKEN_URL` | OAuth token URL | - |
| `GRANT_TYPE` | OAuth grant type | - |
| `SCOPE` | OAuth scope | - |
| `CLIENT_ID` | OAuth client ID | - |
| `CLIENT_SECRET` | OAuth client secret | - |
| `REQUEST_TIMEOUT` | Request timeout in seconds | `30.0` |
| `POOL_CONNECTIONS` | Number of connection pool connections | `100` |
| `POOL_MAXSIZE` | Maximum pool size | `100` |

#### CP4BA Environment Variables

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `ZENIAM_ZEN_URL` | Zen url to send IAM token for exchange to Zen token, for example: <zen_host_route>/v1/preauth/validateAuth | - |
| `ZENIAM_ZEN_SSL_ENABLED` | Whether SSL is enabled for Zen exchange route. Can be set to `true`, a path to a certificate file, or `false` (not recommended for production) | `true` |
| `ZENIAM_IAM_URL` | IAM url to send user/pwd or client_id/client_secret to IAM to get back IAM token, for example: <iam_host_route>/idprovider/v1/auth/identitytoken | - |
| `ZENIAM_IAM_SSL_ENABLED` | Whether SSL is enabled for IAM route. Can be set to `true`, a path to a certificate file, or `false` (not recommended for production) | `true` |
| `ZENIAM_IAM_GRANT_TYPE` |  IAM grant type | - |
| `ZENIAM_IAM_SCOPE` | IAM scope | - |
| `ZENIAM_IAM_USER` | if grant type is password, specify the IAM user | - |
| `ZENIAM_IAM_PASSWORD` | if grant type is password, specify the IAM password  | - |
| `ZENIAM_CLIENT_ID` | if grant type is client_credentials, specify the IAM client id | - |
| `ZENIAM_CLIENT_SECRET` | if grant type is client_credentials, specify the IAM client secret  | - |
#### SSL Configuration Best Practices

For SSL configuration (`SSL_ENABLED`, `TOKEN_SSL_ENABLED`, `ZENIAM_ZEN_SSL_ENABLED`, and `ZENIAM_IAM_SSL_ENABLED`), you have three options:

1. **Use System Certificates (Recommended for Production)**: Set to `true` to use your system's certificate store.

2. **Provide Custom Certificate Path**: Set to the file path of your certificate (e.g., `/path/to/certificate.pem`).

3. **Disable SSL Verification (Not Recommended for Production)**: Set to `false` to disable SSL verification.

> **Security Warning**: Disabling SSL verification (`false`) should only be used in testing environments. For production deployments, always use proper certificate validation to ensure secure communications.

### Authentication Methods

The server supports two authentication methods:

#### Basic Authentication

Set the following environment variables:
```
SERVER_URL=https://your-graphql-endpoint
USERNAME=your_username
PASSWORD=your_password
OBJECT_STORE=your_object_store
SSL_ENABLED=your_path_to_graphql_certificate | true | false
```

#### OAuth Authentication

Set the following environment variables:
```
SERVER_URL=https://your-graphql-endpoint
USERNAME=your_username
PASSWORD=your_password
TOKEN_URL=https://your-oauth-server/token
GRANT_TYPE=password
SCOPE=openid
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
OBJECT_STORE=your_object_store
```
#### Zen/IAM Authentication

An example of ZEN/IAM environment variables when using USER/PASSWORD and SSL to all external servers
```
SERVER_URL=https://your-graphql-endpoint
SSL_ENABLED=your_path_to_graphql_certificate| true | false
OBJECT_STORE=your_object_store
ZENIAM_ZEN_URL=https://your-zen-exchange-route
ZENIAM_ZEN_SSL_ENABLED=your_path_to_zen_exchange_route_certicate | true | false
ZENIAM_IAM_URL=https://your-IAM-route
ZENIAM_IAM_SSL_ENABLED=your_path_to_IAM_route_certicate | true | false
ZENIAM_IAM_GRANT_TYPE=password
ZENIAM_IAM_SCOPE=openid
ZENIAM_IAM_USER=your_user_name
ZENIAM_IAM_PASSWORD=your_user_password
```

### Integration with MCP Clients/Agent Frameworks

#### Claude Desktop Configuration

1. Open Claude Desktop Settings:
   - On macOS, click the Claude menu in the top menu bar and select **Settings**.
   - On Windows, access **Settings** from the Claude application.
     ![Screenshot showing Settings](docs/images/claude-settings.png)

2. Navigate to the **Developer** tab and click **Edit Config**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
     ![Screenshot showing "Edit Config"](docs/images/claude-config.png)
     
3. Add one of the following configuration examples to the **claude_desktop_config.json** file:

   **Option 1: Using local installation (if you've cloned the repository)**
   ```json
   {
     "mcpServers": {
       "core-cs-mcp-server": {
         "command": "/path/to/your/uvx",
         "args": [
           "--from",
           "/path/to/your/cs-mcp-server",
           "core-cs-mcp-server"
         ],
         "env": {
           "USERNAME": "your_username",
           "PASSWORD": "your_password",
           "SERVER_URL": "https://your-graphql-server/content-services-graphql/graphql",
           "OBJECT_STORE": "your_object_store"
         }
       }
     }
   }
   ```

   **Option 2: Installing directly from GitHub (recommended)**
   ```json
   {
     "mcpServers": {
       "core-cs-mcp-server": {
         "command": "uvx",
         "args": [
           "--from",
           "git+https://github.com/ibm-ecm/cs-mcp-server",
           "core-cs-mcp-server"
         ],
         "env": {
           "USERNAME": "your_username",
           "PASSWORD": "your_password",
           "SERVER_URL": "https://your-graphql-server/content-services-graphql/graphql",
           "OBJECT_STORE": "your_object_store"
         }
       }
     }
   }
   ```

4. Restart Claude Desktop:
   - Simply closing the window is not enough, Claude Desktop must be stopped and restarted:
     - on macOS: Claude > Quit
     - on Windows: File > Exit

5. Check Available Tools:
   - To see all the availabel tools in Claude Desktop, proceed as follows:
     - first click the settings icon, and you should see:
       ![Screenshot showing MCP Servers](docs/images/claude-mcp-tools.png)
     - then click `core-cs-mcp-server`, and you should see all your tools:
       ![Screenshot showing Claude tools](docs/images/claude-mcp-tools-details.png)

> **Note:** The JSON configuration examples above show only the minimum required environment variables. For a complete list of all possible configuration options, refer to the Environment Variables tables above.

#### Watson Orchestrate (WxO) Configuration

This section explains how to augment IBM watsonx Orchestrate with the Core Content Services MCP Server, enabling watsonx Orchestrate to interact with IBM FileNet Content Management during user interactions in a chat.

##### Configuration

###### 1. Configure Connection Variables

**For SaaS or on-premises offering (UI):**

- Click the main menu icon
- Navigate to **Manage > Connections**
- Click **Add New Connection**
- Enter connection ID and display name
- Click **Next**
- You will now configure draft connection details (test environment)
  - Select authentication type dropdown to be **Key value pair**
  - Enter each required variable:
    - `SERVER_URL`: Your Content Services GraphQL API endpoint URL
    - `USERNAME`: Authentication username
    - `PASSWORD`: Authentication password
    - `OBJECT_STORE`: Object store identifier
  - Enter any optional variables as needed (e.g., `SSL_ENABLED`, `TOKEN_REFRESH`, etc.)
  - Click **Next** when done
- Now you will enter your live connection environment variables
  - Select authentication type dropdown to be **Key value pair**
  - Enter the same required variables as above
  - Enter any optional variables as needed
  - Select the preferred credential type
  - Click **Add Connection**

**For ADK (Application Development Kit):**

For creating connections using the ADK CLI, please refer to the [official documentation](https://developer.watson-orchestrate.ibm.com/connections/build_connections#importing-from-a-file).

###### 2. Create an agent

- Click the main menu icon
- Navigate to **Build > Agent Builder**

  ![Build > Agent Builder](docs/images/wxo-agent-builder.png)

- Navigate to **All agents**
- Click **Create agent +** to add a new agent

  ![Create an agent](docs/images/wxo-create-agent.png)

- Choose **Create from scratch**
- Enter a **Name** (e.g., `Core Content Services Agent`)
- Enter a **Description** (e.g., `This agent enables interaction with FileNet Content Management.`)
- Click **Create**
  
  ![Create an agent (continued)](docs/images/wxo-create-agent2.png)

###### 3. Augment the agent with the Core Content Services MCP Server

- Navigate to the **Toolset** section, click **Add tool +**

  ![Add tools +](docs/images/wxo-add-tools.png)

- Click **Import**

  ![Import MCP Server](docs/images/wxo-import-mcp-server.png)

- Click **Import from MCP server**

  ![Import MCP Server (continued)](docs/images/wxo-import-mcp-server2.png)

- Click **Add MCP server**

  ![Add MCP Server](docs/images/wxo-add-mcp-server.png)

- Enter a **Server name** without any space characters (e.g., `core-cs-mcp-server`)
- Optionally enter a **Description** (e.g., `This MCP Server connects to FileNet Content Platform Engine, enabling content management operations.`)
- Enter an **Install command**:
  ```
  uvx --from git+https://github.com/ibm-ecm/cs-mcp-server core-cs-mcp-server
  ```
- Click **Connect**
- If you see "Connection successful", click **Done**

  ![Add MCP Server (continued)](docs/images/wxo-add-mcp-server2.png)
  
- Set the **Activation toggle** to **On** for the tools you want to enable

  ![Enable Tools](docs/images/wxo-enable-tools.png)

- Associate your previously created connection with this agent

###### 4. Deploy the agent

- Click **Deploy**

  ![Configuration completed](docs/images/wxo-deploy-agent.png)

- In the popup, Click **Deploy** again

###### 5. Let the agent be used in chats

- Click the main menu icon
- Navigate to **Chat**
- Click the newly created agent

  ![select the agent](docs/images/wxo-select-agent.png)

##### Example Workflow

Once configured, you can interact with your FileNet repository through natural language in watsonx Orchestrate chats, depending on which tool you've enabled. For example:

- "Find all documents containing the pdf in its document title"
- "Create a new folder called Project Z"

  ![chat](docs/images/wxo-chat.png)

Click **Show Reasoning** in any response to see the details of the operations performed.

  ![chat reasoning](docs/images/wxo-chat-reasoning.png)

---

## Usage

### Running the Server Directly

If you have a local copy of the repository, you can run the server directly with:

```bash
USERNAME=your_username PASSWORD=your_password SERVER_URL=https://your-graphql-server/content-services-graphql/graphql OBJECT_STORE=your_object_store /path/to/your/uvx --from /path/to/your/cs-mcp-server core-cs-mcp-server
```

### Integration with AI Agents

The Core Content Services MCP Server can be integrated with AI Agents that support the MCP protocol. This allows the AI Agent to:

1. Access and retrieve document properties
2. Extract text from documents
3. Create, update, check-in, and check-out documents
4. Manage folders and document classifications
5. Execute searches
6. Get document annotations

### Example Workflow

1. **Search and Discovery**:
   - Users typically start with descriptive information (name, content, keywords) rather than IDs
   - The AI Agent first uses search tools to locate relevant objects:
     - `get_searchable_property_descriptions` to discover valid search properties
     - `repository_object_search` for property-based searches
   - Search results include object IDs needed for subsequent operations

2. **Document Retrieval**:
   - Once an object ID is obtained through search, the AI Agent can retrieve:
     - Document properties using the ID
     - Version history
     - Text content (requires Persistent Text Extract Add-on to be installed)
     - Annotations

3. **Document Creation**:
   Users can ask the AI Agent to create new documents with specific properties and content.

4. **Document Update**:
   - After identifying a document through search, the AI Agent can:
     - Check out the document using its ID
     - Update properties or content
     - Check the document back in

5. **Folder Operations**:
   - Folders can be identified by path or by ID from search results
   - Documents can be filed/unfiled using both document and folder IDs


> **Note:** Most operations that modify or access specific objects require an object ID, which is typically obtained through a search operation first. This workflow pattern ensures users can work with objects by their meaningful attributes rather than requiring them to know technical identifiers upfront.

---

## License

See the [LICENSE](LICENSE) file for details.

```text
Licensed Materials - Property of IBM (c) Copyright IBM Corp. 2019,2025 All Rights Reserved.

US Government Users Restricted Rights - Use, duplication or disclosure restricted by GSA ADP Schedule Contract with
IBM Corp.

DISCLAIMER OF WARRANTIES :

Permission is granted to copy and modify this Sample code, and to distribute modified versions provided that both the
copyright notice, and this permission notice and warranty disclaimer appear in all copies and modified versions.

THIS SAMPLE CODE IS LICENSED TO YOU AS-IS. IBM AND ITS SUPPLIERS AND LICENSORS DISCLAIM ALL WARRANTIES, EITHER
EXPRESS OR IMPLIED, IN SUCH SAMPLE CODE, INCLUDING THE WARRANTY OF NON-INFRINGEMENT AND THE IMPLIED WARRANTIES OF
MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. IN NO EVENT WILL IBM OR ITS LICENSORS OR SUPPLIERS BE LIABLE FOR
ANY DAMAGES ARISING OUT OF THE USE OF OR INABILITY TO USE THE SAMPLE CODE, DISTRIBUTION OF THE SAMPLE CODE, OR
COMBINATION OF THE SAMPLE CODE WITH ANY OTHER CODE. IN NO EVENT SHALL IBM OR ITS LICENSORS AND SUPPLIERS BE LIABLE
FOR ANY LOST REVENUE, LOST PROFITS OR DATA, OR FOR DIRECT, INDIRECT, SPECIAL, CONSEQUENTIAL, INCIDENTAL OR PUNITIVE
DAMAGES, HOWEVER CAUSED AND REGARDLESS OF THE THEORY OF LIABILITY, EVEN IF IBM OR ITS LICENSORS OR SUPPLIERS HAVE
BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
```

---

