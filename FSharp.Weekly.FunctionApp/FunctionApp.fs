namespace FSharp.Weekly

open System
open System.Threading.Tasks
open Microsoft.Azure.WebJobs
open Microsoft.Extensions.Logging

module FunctionApp =

    [<FunctionName("FSharpWeekly")>]
    let run([<TimerTrigger("0 0 1 * * *")>]myTimer: TimerInfo, log: ILogger) = // RunOnStartup=true
        Storage.configuredBlobStorage()
        |> Report.generateWeekly log
        :> Task
