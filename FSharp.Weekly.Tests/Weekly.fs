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
    Twitter.auth()
    let tweets =
        Twitter.searchTweets "#fsharp OR #FsAdvent OR #fsharpx OR #FsAdventJP"
        |> List.concat
    printfn "Fount %d tweets" (tweets.Length)
    Assert.GreaterOrEqual(tweets.Length, 0)