namespace FSharp.Weekly

open System.Threading.Tasks
open Microsoft.Azure.WebJobs
open Microsoft.Extensions.Logging

module FunctionApp =

    [<FunctionName("FSharpWeekly")>]
    let fsharpWeekly([<TimerTrigger("0 0 1 * * *")>]myTimer: TimerInfo, log: ILogger) = // RunOnStartup=true
        Storage.configuredBlobStorage()
        |> Report.generateWeekly log
        :> Task

    [<FunctionName("FSharpTweets")>]
    let fsharpTweets([<TimerTrigger("0 0 3 * * *")>]myTimer: TimerInfo, log: ILogger) =
        Storage.configuredTableStorage()
        |> Report.saveFsharpTweets log
        :> Task
