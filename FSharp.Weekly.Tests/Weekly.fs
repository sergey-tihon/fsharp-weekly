module FSharp.Weekly.Tests.Weekly

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
    let client = Twitter.getClient()
    let batches = Twitter.searchTweets client "#fsharp OR #FsAdvent OR #fsharpx OR #FsAdventJP"
    let tweets = batches |> List.concat
    printfn $"Fount %d{tweets.Length} tweets %A{batches |> List.map (List.length)}"
    Assert.GreaterOrEqual(tweets.Length, 0)
