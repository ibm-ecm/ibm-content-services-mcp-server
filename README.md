# Deprecation Notice & Production Warning
>
> **Notice**: This project is nearing end-of-life and will be officially deprecated.
>
> - **Do not use in production**: New implementations should not use this project.

# IBM Content Services MCP Server

## Overview

The IBM Content Services MCP Server provides a standardized interface that enables IBM FileNet Content Manager (FNCM) capabilities to be used by AI models. The server is available in four specialized configurations to support different workflows:

- **Core Server**: Comprehensive document and content management operations
- **Property Extraction and Classification Server**: Document analysis for property extraction and classification
- **Legal Hold Server**: Legal hold management
- **AI Document Insight Server**: Uses virtual table capabilities for Content Assistant vector search combined with property/metadata search, along with document summarization, comparison, and Q&A

Each server can be deployed independently or in combination to support your specific use cases.

---

## Server Types and Capabilities

### Core Server (`core-cs-mcp-server`)

**Purpose**: Comprehensive document and content management operations

**Use Cases**:
- General document lifecycle management (create, update, check-in, check-out, delete)
- Folder operations and document filing
- Search and retrieval across the repository
- Metadata and class management
- Resources support for exposing documents as LLM context

### Property Extraction and Classification Server (`property-extraction-and-classification-cs-mcp-server`)

**Purpose**: Document analysis for property extraction and classification

**Dependencies**: Requires Core Server for document update operations (e.g., `update_document_properties`)

**Use Cases**:
- Automated property extraction from document content
- Document classification and reclassification workflows
- Content-based metadata enrichment

### Legal Hold Server (`legal-hold-cs-mcp-server`)

**Purpose**: Legal hold management

**Use Cases**:
- Creating and managing legal holds
- Placing documents and objects under hold
- Tracking held objects

### AI Document Insight Server (`ai-document-insight-cs-mcp-server`)

**Purpose**: Uses virtual table capabilities for Content Assistant vector search combined with property/metadata search, along with document summarization, comparison, and Q&A

**Dependencies**:
- Requires Core Server for document operations
- Requires Persistent Text Extract add-on
- Requires Content Assistant add-on
- Requires FileNet 5.7.0 IF003 or later

**Use Cases**:
- Content-based document search with metadata filtering using Content Assistant API vector search
- Content Assistant API document summaries
- Content Assistant API document comparison and analysis

---

## Tools List

### Core Server Tools

The Core Server provides 26 tools organized into the following categories:

#### Document Management (11 tools)

- **get_document_versions**: Retrieves a document's version history, including major and minor version numbers and document IDs for each version.

- **get_document_text_extract**: Extracts text content from a document by retrieving its text extract annotations. If multiple text extracts are found, they are concatenated. **IMPORTANT:** This functionality requires the Persistent Text Extract add-on to be installed in your object store. See the [Prerequisites](#prerequisites) section for more details.

- **create_document**: Creates a new document in the content repository with specified properties. Can upload files as the document's content if file paths are provided. Requires first calling determine_class and get_class_property_descriptions.

- **update_document_properties**: Updates an existing document's properties without changing its class. Requires first calling get_class_property_descriptions to get valid properties for the document's current class.

- **update_document_class**: Changes a document's class in the content repository. **WARNING:** Changing a document's class can result in loss of properties if the new class does not have the same properties as the old class. Requires first calling determine_class to get the new class_identifier.

- **checkin_document**: Checks in a document that was previously checked out. Can upload new content files during check-in if file paths are provided.

- **checkout_document**: Checks out a document for editing. Can download the document content to a specified folder path if provided.

- **cancel_document_checkout**: Cancels a document checkout in the content repository, releasing the reservation.

- **get_document_properties**: Retrieves a document from the content repository by ID or path, returning the document object with its properties.

- **delete_document_version**: Deletes a specific document version in the content repository using its document ID.

- **delete_version_series**: Deletes an entire version series (all versions of a document) in the content repository using the version series ID.

#### Folder Management (7 tools)

- **create_folder**: Creates a new folder in the content repository with specified name, parent folder, and optional class identifier.

- **delete_folder**: Deletes a folder from the repository using its ID or path.

- **unfile_document**: Removes a document from a folder without deleting the document itself.

- **file_document**: Files a document into a folder.

- **update_folder**: Updates an existing folder's properties. Requires first calling determine_class and get_class_property_descriptions.

- **get_folder_documents**: Get documents contained in a folder.

- **get_folder_detail**: Retrieves detailed information about a folder.

#### Class/Metadata Management (3 tools)

- **list_root_classes**: Lists root classes.

- **determine_class**: Determines the appropriate class based on the available classes and the content of the user's message or context document.

- **get_class_property_descriptions**: Retrieves detailed descriptions of all properties for a specified class.

#### Search (5 tools)

- **get_searchable_property_descriptions**: Retrieves descriptions of properties that can be used in search operations.

- **repository_object_search**: Searches for repository objects based on specified criteria.

- **document_search**: Searches for documents based on content and/or metadata criteria using full-text CBR search. Can combine content-based search with property filters for precise document discovery. Returns only released versions of documents. Special characters in content search terms are automatically escaped.

- **lookup_documents_by_name**: Searches for documents by matching keywords against document names. Returns a ranked list of matching documents with confidence scores. Useful when you know part of a document's name but not its exact ID or path.

- **lookup_documents_by_path**: Searches for documents based on their location in the folder hierarchy. Matches keywords against folder names and document containment names at each path level. Particularly useful when the user describes a document using path separators (e.g., "/Folder1/Subfolder/document").

### Property Extraction and Classification Server Tools

The Property Extraction and Classification Server provides 2 specialized tools for AI-powered document workflows:

- **property_extraction**: Extracts document class, properties metadata, and text content for AI-based property value extraction. This tool determines the document's class, fetches class metadata to identify all available properties (filtering out system and hidden properties), and retrieves the document's text extract content.

- **list_all_classes**: Lists all available classes for a specific root class type. Essential for document reclassification workflows where you need to match document content to the most appropriate class.

### Legal Hold Server Tools

The Legal Hold Server provides 6 tools for legal compliance management:

- **create_hold**: Creates a new legal hold with a specified display name.

- **delete_hold**: Removes a legal hold and releases all held objects.

- **add_object_to_hold**: Places an object (document, folder, etc.) under a legal hold.

- **delete_object_from_hold**: Removes an object from a legal hold without deleting the hold itself.

- **get_held_objects_for_hold**: Lists all objects currently under a specific legal hold.

- **get_holds_by_name**: Searches for legal holds by their display name.

### AI Document Insight Server Tools 

The AI Document Insight Server provides 6 specialized tools that leverage virtual table capabilities for Content Assistant operations:

- **document_smart_search**: Performs a hybrid search combining vector (semantic) search and metadata filtering to find documents. Use this to find relevant documents based on meaning rather than just keywords. Returns only released versions of documents ranked by a GenaiScore.

- **document_quick_summary**: Generates a concise AI-powered summary for one or more provided document IDs. Use this to give the user a quick overview of content without reading the full text.

- **document_compare_insights**: Compares exactly two documents to identify similarities, differences, and version changes. Returns an AI-generated analysis.

- **document_qa_global**: Answers natural language questions by scanning the entire document repository. Use this for broad questions where the specific documents are not known or when looking for patterns across the entire document repository.

- **document_qa_specific**: Answers natural language questions based strictly on the context of specific, selected document. Use this when the user asks about a specific file.

- **documents_qa_multiple**: Answers natural language questions based strictly on the context of selected documents. Use this when the user asks about a set of files.

---

## Resources

### What are Resources?

Resources provide read-only access to document content for LLM context. Documents in configured folders are automatically exposed as MCP resources, allowing AI models to reference them during conversations without explicit tool calls.

> **Important:** Resources functionality requires the **Persistent Text Extract Add-on** to be installed in your object store to retrieve document content. See the [Prerequisites](#prerequisites) section for installation details.

### Server-Specific Resource Support

Each server type supports resources with specific folder defaults and optional prefix validation:

| Server Type | Default Folder | Prefix Requirement | Description |
|-------------|----------------|-------------------|-------------|
| **Core** | `/resources` | None | Accepts all documents without prefix validation |
| **AI Document Insight** | `/resources/AIDocumentInsight` | `DI_` | Only loads documents starting with `DI_` |
| **Legal Hold** | `/resources/LegalHold` | `LH_` | Only loads documents starting with `LH_` |
| **Property Extraction & Classification** | `/resources/Classification` | `CL_`, `PE_` | Only loads documents starting with `CL_` or `PE_` |

### Configuration

#### RESOURCES_FOLDER

Override the default resource folder path for any server:

```bash
RESOURCES_FOLDER=/custom/path  # Override default folder path
```

The `RESOURCES_FOLDER` value is the path of the folder in your FileNet object store where you should upload your resource documents. The server will automatically discover and register all documents in this folder.

Documents in the configured folder will be:
- Automatically registered as resources when the server starts
- Available to the LLM with URIs following the pattern: `ibm-cs://{object_store}/documents/{folder_path}/{document_name}`
- Displayed with names in the format: `[IBM CS] {document_name}`

#### RESOURCES_PREFIX_VALIDATION

Control how the server validates document name prefixes:

```bash
RESOURCES_PREFIX_VALIDATION=warn  # Default: warn
```

**Validation Modes:**

- **`strict`**: Documents without matching prefixes are skipped and logged as errors. Recommended for production to ensure clean separation between server types.
- **`warn`** (Default): Documents without matching prefixes are skipped with warnings logged. Good for development and testing.
- **`off`**: No prefix validation performed. All documents in the folder are loaded regardless of naming.

**Example for Legal Hold Server:**
```bash
# Uses default folder: /resources/LegalHold
# Only accepts documents starting with LH_
# Strict validation - logs errors for invalid documents
RESOURCES_PREFIX_VALIDATION=strict
```

### Security Guidelines

**Access Control:** The resources folder should only be modifiable by administrative users to prevent tampering with content that will be used by AI models. Configure appropriate folder permissions in your FileNet object store to:
- Restrict write/modify access to administrators only
- Allow read access for the MCP server business user
- Prevent unauthorized users from adding, modifying, or deleting resource documents

### Use Cases

Resources are ideal for providing AI models with reference documentation:
- Policy documents for compliance guidance
- Classification guidelines for document categorization
- Standard operating procedures
- Regulatory requirements
- Best practices documentation

### Example

**For Core Server (default folder: `/resources`, no prefix required):**

Documents in that folder:
- `/resources/data_classification_policy.txt`
- `/resources/retention_policy.txt`

**For Property Extraction & Classification Server (default folder: `/resources/Classification`, requires `CL_` or `PE_` prefix):**

Documents with proper prefixes:
- `/resources/Classification/CL_data_classification_policy.txt`
- `/resources/Classification/CL_retention_policy.txt`

Or to load files without prefix validation:
```bash
RESOURCES_PREFIX_VALIDATION=off
```
Documents without prefixes:
- `/resources/Classification/data_classification_policy.txt`
- `/resources/Classification/retention_policy.txt`

These documents will be available as resources that the AI can reference when answering questions or making decisions.

---

## Tested Environments

The Content Services MCP Servers have been tested with the following MCP client and LLM combinations:
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
| Watson Orchestrate | Sporadic 'Invalid tool call object' error when agent tries to invoke MCP tools | • `create_document`<br>• `checkin_document`<br>• `checkout_document`<br>• `get_document_versions`<br>• `repository_object_search` |

> **Note:** These limitations are due to the MCP client's input handling capabilities, not the MCP server itself.

---

## Setup and Configuration

### Prerequisites

- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
  - on macOS: `brew install uv`
  - on Windows: see link above
- Access to a FileNet CPE server with Content Services GraphQL API (CS-GQL) installed

#### Required Add-ons

> **Important:** The following add-ons must be installed in your FileNet object store for specific server functionality:

**Persistent Text Extract Add-on** (Required for Core, Property Extraction, and AI Document Insight Servers)
- Enables extraction and storage of text content from documents
- **Required for:**
  - Core Server: `get_document_text_extract` tool and Resources functionality
  - Property Extraction and Classification Server: `property_extraction` tool
  - AI Document Insight Server: All tools (`document_smart_search`, `document_quick_summary`, `document_compare_insights`, `document_qa_global`)
- Without this add-on, document content retrieval features will not work
- For installation instructions, refer to the [IBM Documentation on Installing the Persistent Text Add-on](https://www.ibm.com/docs/en/content-assistant?topic=extraction-installing-persistent-text-add)

**Content Assistant Add-on** (Required for AI Document Insight Server only)
- Provides AI-powered search, summarization, comparison, and Q&A capabilities
- **Required for:** AI Document Insight Server (all tools)
- Includes vector search and GenAI model integration
- For installation instructions, refer to the IBM Content Assistant documentation

**FNCM Deployment Version Requirements**

- **Version 5.5.8 or later** (Required for Core, Legal Hold, and Property Extraction and Classification Servers)
  - Provides the base GraphQL API support required for core content management operations
  - **Required for:** Core Server, Legal Hold Server, and Property Extraction and Classification Server (all tools)

- **Version 5.7.0 IF003 or later** (Required for AI Document Insight Server only)
  - Provides GraphQL virtual table support required for AI document insight operations
  - **Required for:** AI Document Insight Server (all tools)

### Configuration

The Content Services MCP Servers require several environment variables to connect to your FileNet CPE server:

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
| `LOG_LEVEL` | Logging level for the server. Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `INFO` |
| `RESOURCES_FOLDER` | Folder path in the repository containing documents to expose as MCP resources. Each server type has a default folder (see [Resources](#resources) section). Documents will be automatically registered as resources with URIs following the pattern `ibm-cs://{object_store}/documents/{folder_path}/{document_name}`. Resource names will be displayed as `[IBM CS] {document_name}` in MCP clients. Requires Persistent Text Extract Add-on. | Server-specific (see [Resources](#resources)) |
| `RESOURCES_PREFIX_VALIDATION` | Controls prefix validation for resource documents. Valid values: `strict` (skip invalid documents, log errors), `warn` (skip invalid documents, log warnings), `off` (no validation). See [Resources](#resources) section for server-specific prefix requirements. | `warn` |

#### Cloud Pak for Business Automation Environment Variables

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

The server supports three authentication methods:

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
           "git+https://github.com/ibm-ecm/ibm-content-services-mcp-server",
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

   **Option 3: Multi-Server Setup (Core + Property Extraction + Legal Hold + AI Document Insight)**
   ```json
   {
     "mcpServers": {
       "core-cs-mcp-server": {
         "command": "uvx",
         "args": [
           "--from",
           "git+https://github.com/ibm-ecm/ibm-content-services-mcp-server",
           "core-cs-mcp-server"
         ],
         "env": {
           "USERNAME": "your_username",
           "PASSWORD": "your_password",
           "SERVER_URL": "https://your-graphql-server/content-services-graphql/graphql",
           "OBJECT_STORE": "your_object_store"
         }
       },
       "property-extraction-cs-mcp-server": {
         "command": "uvx",
         "args": [
           "--from",
           "git+https://github.com/ibm-ecm/ibm-content-services-mcp-server",
           "property-extraction-and-classification-cs-mcp-server"
         ],
         "env": {
           "USERNAME": "your_username",
           "PASSWORD": "your_password",
           "SERVER_URL": "https://your-graphql-server/content-services-graphql/graphql",
           "OBJECT_STORE": "your_object_store"
         }
       },
       "legal-hold-cs-mcp-server": {
         "command": "uvx",
         "args": [
           "--from",
           "git+https://github.com/ibm-ecm/ibm-content-services-mcp-server",
           "legal-hold-cs-mcp-server"
         ],
         "env": {
           "USERNAME": "your_username",
           "PASSWORD": "your_password",
           "SERVER_URL": "https://your-graphql-server/content-services-graphql/graphql",
           "OBJECT_STORE": "your_object_store"
         }
       },
       "ai-document-insight-cs-mcp-server": {
         "command": "uvx",
         "args": [
           "--from",
           "git+https://github.com/ibm-ecm/ibm-content-services-mcp-server",
           "ai-document-insight-cs-mcp-server"
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
   - To see all the available tools in Claude Desktop, proceed as follows:
     - first click the settings icon, and you should see:
       ![Screenshot showing MCP Servers](docs/images/claude-mcp-tools.png)
     - then click `core-cs-mcp-server`, and you should see all your tools:
       ![Screenshot showing Claude tools](docs/images/claude-mcp-tools-details.png)

> **Note:** The JSON configuration examples above show only the minimum required environment variables. For a complete list of all possible configuration options, refer to the Environment Variables tables above.

#### Watson Orchestrate (WxO) Configuration

This section explains how to augment IBM watsonx Orchestrate with the Content Services MCP Servers, enabling watsonx Orchestrate to interact with IBM FileNet Content Management during user interactions in a chat.

You can configure one or multiple servers depending on your needs:
- **Core Server**: For general document management operations
- **Property Extraction and Classification Server**: For AI-powered document analysis (requires Core Server for document updates)
- **Legal Hold Server**: For legal compliance workflows

The configuration steps below use the Core Server as an example, but the same process applies to other servers by changing the server name and install command.

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
  uvx --from git+https://github.com/ibm-ecm/ibm-content-services-mcp-server core-cs-mcp-server
  ```
  
  **For other servers, use these install commands:**
  - Property Extraction and Classification Server:
    ```
    uvx --from git+https://github.com/ibm-ecm/ibm-content-services-mcp-server property-extraction-and-classification-cs-mcp-server
    ```
  - Legal Hold Server:
    ```
    uvx --from git+https://github.com/ibm-ecm/ibm-content-services-mcp-server legal-hold-cs-mcp-server
    ```
  - AI Document Insight Server:
    ```
    uvx --from git+https://github.com/ibm-ecm/ibm-content-services-mcp-server ai-document-insight-cs-mcp-server
    ```
  
  **Note:** If you encounter issues with git-based installation (e.g., "Git executable not found"), you can use this alternative command that downloads directly from GitHub without requiring git:
  ```
  uvx --from https://github.com/ibm-ecm/ibm-content-services-mcp-server/archive/refs/heads/main.zip core-cs-mcp-server
  ```
  Replace `core-cs-mcp-server` with the name of the server you want to install (`property-extraction-and-classification-cs-mcp-server`, `legal-hold-cs-mcp-server`, or `ai-document-insight-cs-mcp-server`).
  


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

### Running Servers Directly

If you have a local copy of the repository, you can run any server directly with environment variables:

**Core Server:**
```bash
USERNAME=your_username PASSWORD=your_password SERVER_URL=https://your-graphql-server/content-services-graphql/graphql OBJECT_STORE=your_object_store uvx --from /path/to/your/cs-mcp-server core-cs-mcp-server
```

**Property Extraction and Classification Server:**
```bash
USERNAME=your_username PASSWORD=your_password SERVER_URL=https://your-graphql-server/content-services-graphql/graphql OBJECT_STORE=your_object_store uvx --from /path/to/your/cs-mcp-server property-extraction-and-classification-cs-mcp-server
```

**Legal Hold Server:**
```bash
USERNAME=your_username PASSWORD=your_password SERVER_URL=https://your-graphql-server/content-services-graphql/graphql OBJECT_STORE=your_object_store uvx --from /path/to/your/cs-mcp-server legal-hold-cs-mcp-server
```

**AI Document Insight Server:**
```bash
USERNAME=your_username PASSWORD=your_password SERVER_URL=https://your-graphql-server/content-services-graphql/graphql OBJECT_STORE=your_object_store uvx --from /path/to/your/cs-mcp-server ai-document-insight-cs-mcp-server
```

### Integration with AI Agents

The Content Services MCP Servers can be integrated with AI Agents that support the MCP protocol. Depending on which server(s) you deploy, the AI Agent can:

**Core Server capabilities:**
1. Access and retrieve document properties
2. Extract text from documents
3. Create, update, check-in, and check-out documents
4. Manage folders and document classifications
5. Execute searches
6. Access resources for LLM context

**Property Extraction and Classification Server capabilities:**
1. Extract property values from document content using AI
2. List and match document classes for reclassification

**Legal Hold Server capabilities:**
1. Create and manage legal holds
2. Place objects under hold
3. Track and query held objects

**AI Document Insight Server capabilities:**
1. Perform AI-powered hybrid searches combining vector search with metadata filtering
2. Generate document summaries using GenAI
3. Compare documents and analyze differences
4. Answer natural language questions across the entire document repository
5. Answer natural language questions based on one document or a set of documents

### Example Workflows

#### Core Server Workflow: Search and Document Management

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

#### Property Extraction and Classification Workflow

**Requires:** Core Server (for document updates)

1. **Property Extraction**:
   - Use `property_extraction` tool with a document ID
   - The tool returns:
     - Document class information
     - All available properties for that class (excluding system/hidden properties)
     - Document text content
   - AI analyzes the text and extracts appropriate property values
   - Use Core Server's `update_document_properties` to save the extracted values

2. **Document Classification**:
   - Use `list_all_classes` to get all available document classes
   - AI analyzes document content and matches it to the most appropriate class
   - Use Core Server's `update_document_class` to reclassify the document

#### Legal Hold Workflow

1. **Creating a Hold**:
   - Use `create_hold` with a descriptive name (e.g., "Litigation ABC vs XYZ")
   - Returns the hold object with its ID

2. **Placing Objects Under Hold**:
   - Identify documents using Core Server search tools (if needed)
   - Use `add_object_to_hold` with the hold ID and object ID
   - Repeat for all relevant documents/objects

3. **Managing Holds**:
   - Use `get_holds_by_name` to find holds by name
   - Use `get_held_objects_for_hold` to see all objects under a specific hold
   - Use `delete_object_from_hold` to release specific objects
   - Use `delete_hold` to remove the hold entirely (releases all objects)

> **Note:** Most operations that modify or access specific objects require an object ID, which is typically obtained through a search operation first. This workflow pattern ensures users can work with objects by their meaningful attributes rather than requiring them to know technical identifiers upfront.

---

## License

See the [LICENSE](LICENSE) file for details.

```
# Copyright contributors to the IBM Content Services MCP Server project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

---

