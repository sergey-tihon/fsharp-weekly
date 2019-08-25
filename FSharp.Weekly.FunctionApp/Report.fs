module FSharp.Weekly.Report

open System
open System.Threading.Tasks
open System.Globalization
open Microsoft.Extensions.Logging
open FSharp.Control.Tasks
open Giraffe
open Tweetinvi
open FSharp.Weekly.Twitter

let getReportFileName () =
    let now = DateTime.Now
    let calendar = CultureInfo.InvariantCulture.Calendar
    let day  = calendar.GetDayOfWeek(now) |> int
    let dayDelta = 4 - (if day = 0 then 7 else day)
    let week = calendar.GetWeekOfYear(now.AddDays(float dayDelta), CalendarWeekRule.FirstFourDayWeek, DayOfWeek.Monday)
    sprintf "FsharpWeekly%d-week%d__%s.html" now.Year week (now.ToString("MM-dd__HH-mm"))

let generateWeekly (log: ILogger) (storage:Storage.IStorage) = task {
    Twitter.auth()

    let loadTweets query ty =
        let batches = searchTweets query
        let tweets = batches |> List.concat

        sprintf "Found %d tweets by query '%s' with batches %A"
            (tweets.Length) query
            (batches |> List.map (List.length))
        |> log.LogInformation

        tweets |> List.map (fun t -> {
            Tweet = flatTweet t
            Query = query
            TweetType = ty
            Origin = t.CreatedBy.Name
        })

    let tweets = [
        yield! loadTweets "from:sergey_tihon OR from:dsyme OR from:c4fsharp OR from:dotnet" AllTweets
        yield! loadTweets "#fsharp OR #FsAdvent OR #fsharpx OR #FsAdventJP" OnlyWithLinks
        yield! loadTweets "fsharp -#fsharp -from:FSharp_Ace" BeCareful
    ]
    log.LogInformation <| sprintf "Loaded %d tweets" (tweets.Length)

    // Execution time optimized for Consumption based App Service Plan
    let! saveTweet = storage "tweets"
    let mutable savedTweetsCount = 0
    for nt in tweets do
        let json = nt.Tweet.ToJson()
        let filename = nt.Tweet.IdStr + ".json"
        let! isSaved = saveTweet filename json false
        if isSaved then savedTweetsCount <- savedTweetsCount + 1
    log.LogInformation <| sprintf "Saved %d NEW tweets in JSONs" savedTweetsCount

    let startDate = DateTime.Now - TimeSpan.FromDays(7.0)
    let tweets =
        tweets
        |> List.filter (fun x -> x.Tweet.CreatedAt > startDate)
        |> List.filter (fun x ->
            match x.TweetType with
            | AllTweets -> true
            | _ -> x.Tweet.Urls.Count > 0)
        |> List.distinctBy (fun x -> x.Tweet.Id)
        |> List.sortBy (fun x -> x.Tweet.CreatedAt)


    let! htmlReport = Templates.report tweets (Twitter.oEmbed)
    let htmlReport = GiraffeViewEngine.renderHtmlDocument htmlReport

    let! saveReport = storage "reports"
    let! _ = saveReport "latest.html" htmlReport true

    let reportName = getReportFileName()
    let! isSaved = saveReport reportName htmlReport false
    if isSaved
    then log.LogInformation <| sprintf "F# Weekly saved to %s" reportName
    else log.LogError <| sprintf "F# weekly NOT saved to %s" reportName
}

