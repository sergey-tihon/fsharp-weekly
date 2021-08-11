module FSharp.Weekly.Report

open System
open System.Threading.Tasks
open System.Globalization
open System.Collections.Generic
open Microsoft.Extensions.Logging
open FSharp.Control.Tasks
open FSharp.Weekly.Storage
open FSharp.Weekly.Twitter
open FSharp.Weekly.Templates
open Tweetinvi.Models

let getReportFileName () =
    let now = DateTime.UtcNow
    let calendar = CultureInfo.InvariantCulture.Calendar
    let day  = calendar.GetDayOfWeek(now) |> int
    let dayDelta = 4 - (if day = 0 then 7 else day)
    let week = calendar.GetWeekOfYear(now.AddDays(float dayDelta), CalendarWeekRule.FirstFourDayWeek, DayOfWeek.Monday)
    sprintf "FsharpWeekly%d-week%d__%s.html" now.Year week (now.ToString("MM-dd__HH-mm"))

let generateWeekly (logger: ILogger) (storage:Storage.IStorage) = task {
    let client = Twitter.getClient()

    let logs = List<_>()
    let log text =
        logs.Add text
        logger.LogInformation text

    let loadTweets query ty =
        let batches = searchTweets client query
        let tweets = batches |> List.concat

        log <| $"Found %d{tweets.Length} tweets by query '%s{query}' with batches %A{batches |> List.map (List.length)}"

        tweets |> List.map (fun t -> {
            Tweet = flatTweet t
            Query = query
            TweetType = ty
            Origin = t.CreatedBy.Name
            IsDuplicate = false
        })

    let tweets = [
        yield! loadTweets "from:sergey_tihon OR from:dsyme OR from:c4fsharp OR from:dotnet" AllTweets
        yield! loadTweets "#fsharp OR #FsAdvent OR #fsharpx OR #FsAdventJP" OnlyWithLinks
        yield! loadTweets "fsharp -#fsharp -from:FSharp_Ace" BeCareful
    ]
    log <| $"Loaded %d{tweets.Length} tweets"

    let links = Dictionary<_,_>(StringComparer.InvariantCultureIgnoreCase)
    let startDate = DateTimeOffset.Now - TimeSpan.FromDays(7.0)
    let tweets =
        tweets
        |> List.filter (fun x -> x.Tweet.CreatedAt > startDate)
        |> List.distinctBy (fun x -> x.Tweet.Id)
        |> List.sortBy (fun x -> x.Tweet.CreatedAt)
        |> List.choose (fun x ->
            let isNewLink =
                x.Tweet.Urls
                |> Seq.fold (fun state url ->
                    if links.TryAdd(url.ExpandedURL, x.Tweet.Url)
                    then true else state
                   ) false

            match x.TweetType with
            | AllTweets -> Some(x)
            | _ ->
                if x.Tweet.Urls.Count = 0 then None
                elif isNewLink then Some (x)
                else Some ({x with IsDuplicate = true})
          )

    log <| $"%d{tweets.Length} tweets included in final report"
    let model = {
        NewsTweets = tweets
        Logs = List.ofSeq logs
        Links = List.ofSeq links |> List.map (fun x-> x.Key, x.Value) |> List.sortBy fst
    }

    let! htmlReport = Templates.report model (Twitter.oEmbed)
    let htmlReport = Giraffe.ViewEngine.RenderView.AsString.htmlDocument htmlReport

    let! saveReport = storage "reports"
    let! _ = saveReport "latest.html" htmlReport true

    let reportName = getReportFileName()
    let! isSaved = saveReport reportName htmlReport false
    if isSaved
    then logger.LogInformation <| $"F# Weekly saved to %s{reportName}"
    else logger.LogError <| $"F# weekly NOT saved to %s{reportName}"
}

let saveFsharpTweets (log: ILogger) (storage:string->Task<TweetRow -> Task<bool>>) = task {
    let client = Twitter.getClient()

    let tweets = searchTweets client "#fsharp" |> List.concat
    log.LogInformation <| $"Loaded %d{tweets.Length} '#fsharp' tweets"

    // Execution time optimized for Consumption based App Service Plan
    let! saveTweet = storage "fsharptweets"
    let mutable savedTweetsCount = 0
    for t in tweets do
        let json = client.Json.Serialize<ITweet>(t)
        let tweetRow = Storage.TweetRow(t.Id, t.CreatedAt.UtcDateTime.ToUniversalTime(), t.CreatedBy.ScreenName, t.FullText, json)
        let! isSaved = saveTweet tweetRow
        if isSaved then savedTweetsCount <- savedTweetsCount + 1
    log.LogInformation <| $"Saved %d{savedTweetsCount} NEW #fsharp tweets in Table Storage"
}
