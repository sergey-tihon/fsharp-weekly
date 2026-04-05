# F# Weekly — Agent Instructions

## Project Overview

**F# Weekly** is an Azure Functions v4 application (targeting .NET 8) that generates an HTML weekly digest of F# tweets and stores it in Azure Blob Storage. It also archives `#fsharp` tweets to Azure Table Storage.

### Solution structure

```
fsharp-weekly.sln
├── FSharp.Weekly.FunctionApp/   # Main Azure Functions project
│   ├── Storage.fs               # Blob & Table Storage abstractions
│   ├── Twitter.fs               # Twitter/Tweetinvi client helpers
│   ├── Templates.fs             # Giraffe.ViewEngine HTML templates + domain types
│   ├── Report.fs                # Core report-generation logic
│   └── FunctionApp.fs           # Azure Function entry points (timer triggers)
└── FSharp.Weekly.Tests/         # NUnit test project
    ├── Weekly.fs                # Integration tests for report generation
    ├── FsAdvent.fs              # FsAdvent calendar HTML generator
    ├── TweetsFromMongo.fs       # Migration helper: MongoDB → Azure Table
    └── FsHeroes.fs              # Image-composition utility
```

**F# source files must be listed in `<Compile>` order inside the `.fsproj`** — compilation order matters.

---

## Build Commands

```bash
# Build the entire solution
dotnet build

# Build a specific project
dotnet build FSharp.Weekly.FunctionApp/FSharp.Weekly.FunctionApp.fsproj
dotnet build FSharp.Weekly.Tests/FSharp.Weekly.Tests.fsproj

# Publish the function app
dotnet publish FSharp.Weekly.FunctionApp/FSharp.Weekly.FunctionApp.fsproj -c Release
```

SDK version is pinned to **8.0.403** via `global.json`.

---

## Test Commands

Tests use **NUnit 3** with the NUnit3TestAdapter and Microsoft.NET.Test.Sdk.

```bash
# Run all tests
dotnet test

# Run all tests in the test project
dotnet test FSharp.Weekly.Tests/FSharp.Weekly.Tests.fsproj

# Run a single test by name (use --filter with the test name)
dotnet test FSharp.Weekly.Tests/FSharp.Weekly.Tests.fsproj --filter "FullyQualifiedName~loadTweets"

# Run tests in a specific module
dotnet test FSharp.Weekly.Tests/FSharp.Weekly.Tests.fsproj --filter "FullyQualifiedName~FsAdvent"

# Run with verbose output
dotnet test FSharp.Weekly.Tests/FSharp.Weekly.Tests.fsproj -v normal
```

> **Note:** Most tests are integration tests that require live credentials (Twitter API keys, Azure Storage connection string). Set the required environment variables before running (see Environment Variables below).

---

## Formatting (Fantomas)

The project uses **Fantomas 6.2.2** (registered as a local dotnet tool) for F# code formatting.

```bash
# Restore local tools (first time or after cloning)
dotnet tool restore

# Format all F# files
dotnet fantomas .

# Format a single file
dotnet fantomas FSharp.Weekly.FunctionApp/Report.fs

# Check formatting without writing (CI use)
dotnet fantomas . --check
```

Formatting rules are configured in `.editorconfig`:

| Setting | Value |
|---|---|
| `max_line_length` | 150 |
| `fsharp_max_infix_operator_expression` | 70 |
| `fsharp_multiline_block_brackets_on_same_column` | true |
| `fsharp_single_argument_web_mode` | true |
| `fsharp_multi_line_lambda_closing_newline` | true |
| `fsharp_disable_elmish_syntax` | true |
| `fsharp_blank_lines_around_nested_multiline_expressions` | false |

Always run `dotnet fantomas` before committing changes.

---

## Environment Variables

| Variable | Used in | Description |
|---|---|---|
| `WEEKLY_STORAGE_CONNECTION_STRING` | `Storage.fs` | Azure Storage connection string (Blob + Table) |
| `TWITTER_CONSUMER_KEY` | `Twitter.fs` | Twitter API consumer key |
| `TWITTER_CONSUMER_SECRET` | `Twitter.fs` | Twitter API consumer secret |
| `TWITTER_ACCESS_TOKEN` | `Twitter.fs` | Twitter API access token |
| `TWITTER_ACCESS_SECRET` | `Twitter.fs` | Twitter API access secret |

Missing env vars cause `failwithf` at runtime (see `Storage.getEnvValue`). Local development values go in `FSharp.Weekly.FunctionApp/local.settings.json` (never committed — excluded by `.gitignore`).

---

## Code Style Guidelines

### Language version
- `LangVersion` is set to `preview` — modern F# features (interpolated strings, CEs, etc.) are available.

### Module and namespace conventions
- Top-level files use either `module FSharp.Weekly.ModuleName` (flat) or `namespace FSharp.Weekly` + inner `module` blocks.
- Infrastructure/utility modules (Storage, Twitter) use `[<RequireQualifiedAccess>]` — always call them as `Storage.xxx`, `Twitter.xxx`.
- Template/domain modules do not use `RequireQualifiedAccess` and are opened freely.

### Imports (`open` statements)
- Group `open` statements at the top of each file/module, after the module declaration.
- Standard library first (`System.*`), then third-party (`Microsoft.*`, `Tweetinvi`, `Giraffe`, etc.), then project-internal (`FSharp.Weekly.*`).
- Do not open modules unnecessarily — prefer qualified access for `Storage` and `Twitter`.

### Types and records
- Domain types are defined in `Templates.fs` (the lowest-dependency module before `Report.fs`).
- Use F# records for data shapes: `{ Tweet: ITweet; Query: string; TweetType: TweetType; ... }`.
- Use discriminated unions for enumerations: `type TweetType = AllTweets | OnlyWithLinks | BeCareful`.
- Type aliases for function signatures (`type IStorage = string -> Task<IFileSaver>`) are preferred over raw function types in signatures.

### Async / Task
- Use `task { ... }` computation expressions (not `async { }`) throughout — this project is task-based.
- Return `Task` (not `Task<unit>`) from Azure Function handlers by upcasting: `:> Task`.
- Prefer `Task.WhenAll` for fan-out over sequential awaiting.
- Synchronous blocking of async code (`Async.RunSynchronously`) is used only in `Twitter.fs` for compatibility — avoid adding new instances.

### Error handling
- Missing environment variables raise `failwithf` immediately — fail fast, no silent defaults.
- Boolean return values (`Task<bool>`) indicate success/failure for storage operations; callers log accordingly.
- Do not use exceptions for control flow inside pipeline logic.

### Naming conventions
- Functions: `camelCase` (`generateWeekly`, `getReportFileName`).
- Types/modules: `PascalCase` (`ReportModel`, `TweetRow`, `IStorage`).
- Mutable variables (rare): `camelCase`, prefixed with context (`savedTweetsCount`).
- Use descriptive names; single-letter names only acceptable in short lambdas (`fun t -> ...`, `fun x -> ...`).

### Formatting style
- Prefer pipeline operators (`|>`) over intermediate `let` bindings for sequential transformations.
- Use `$"... %d{x} ..."` interpolated strings (not `sprintf` where avoidable).
- Multiline `list` and `seq` expressions use `yield!` and `yield` explicitly when mixing comprehensions.
- Keep lines under 150 characters (Fantomas will enforce this).
- Indent with 4 spaces (standard F# / Fantomas default).

### HTML templating (Giraffe.ViewEngine)
- Build HTML using `Giraffe.ViewEngine` combinators (`html`, `head`, `body`, `table`, `tr`, `td`, etc.).
- Use `rawText` for pre-formatted HTML (e.g., oEmbed responses); use `str` for plain escaped text.
- Render to string with `RenderView.AsString.htmlDocument`.

### Azure Functions
- Timer triggers are defined with cron expressions: `"0 0 1 * * *"` (seconds included).
- Function names use `[<FunctionName("...")>]` attribute with PascalCase string identifiers.
- Inject `ILogger` directly from the function signature — do not use static loggers.

### Adding new source files
1. Create the `.fs` file in the appropriate project directory.
2. Add a `<Compile Include="NewFile.fs" />` entry in the `.fsproj` at the correct position (respecting dependency order).
3. Files that depend on `Storage.fs` must come after it; files that depend on `Templates.fs` must come after it, etc.

---

## Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| `Microsoft.NET.Sdk.Functions` | 4.1.3 | Azure Functions v4 host |
| `Giraffe.ViewEngine` | 1.4.0 | HTML DSL for report templates |
| `TweetinviAPI` | 5.0.4 | Twitter API client |
| `Microsoft.Azure.Storage.Blob` | 11.2.3 | Azure Blob Storage |
| `Microsoft.Azure.Cosmos.Table` | 1.0.8 | Azure Table Storage |
| `nunit` / `NUnit3TestAdapter` | 3.13.3 / 4.3.1 | Test framework |
| `MongoDB.Driver` | 2.19.0 | Used in migration test only |
| `SixLabors.ImageSharp` | 3.1.3 | Image composition in FsHeroes test |
| `FSharp.Core` | 7.0.0 | Pinned across both projects |
