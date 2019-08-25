module FSharp.Weekly.Tests

open System.Threading.Tasks
open NUnit.Framework
open FSharp.Weekly
open FSharp.Weekly.Storage

open Microsoft.Extensions.DependencyInjection
open Microsoft.Extensions.Logging

let getLogger () =
    let serviceProvider =
        ServiceCollection()
            .AddLogging(fun cfg -> cfg.AddConsole() |> ignore)
            .Configure<_>(fun (cfg:LoggerFilterOptions) -> cfg.MinLevel <- LogLevel.Debug)
            .BuildServiceProvider();
    serviceProvider.GetService<ILogger<IStorage>>()

[<Test>]
let ``Run Report with LocalStorage`` () =
    Storage.localStorage()
    |> Report.generateWeekly (getLogger())
    :> Task

[<Test>]
let ``Run Report with CloudBlobStore`` () =
    Storage.configuredBlobStorage()
    |> Report.generateWeekly (getLogger())
    :> Task


[<Test>]
let loadTweets () =
    Twitter.auth()
    let tweets =
        Twitter.searchTweets "(from:sergey_tihon OR from:dsyme OR from:c4fsharp OR from:dotnet)"
        |> List.concat
    printfn "Fount %d tweets" (tweets.Length)
    Assert.GreaterOrEqual(tweets.Length, 0)