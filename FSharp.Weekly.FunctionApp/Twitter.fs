module FSharp.Weekly.Twitter

open System
open System.Net.Http
open FSharp.Control.Tasks
open Newtonsoft.Json
open Newtonsoft.Json.Linq
open Tweetinvi
open Tweetinvi.Parameters
open Tweetinvi.Models

let auth () =
    let consumerKey = Storage.getEnvValue "TWITTER_CONSUMER_KEY"
    let consumerSecret = Storage.getEnvValue "TWITTER_CONSUMER_SECRET"
    let userAccessToken = Storage.getEnvValue "TWITTER_ACCESS_TOKEN"
    let userAccessSecret = Storage.getEnvValue "TWITTER_ACCESS_SECRET"
    Auth.SetUserCredentials(
        consumerKey, consumerSecret,
        userAccessToken, userAccessSecret)
    |> ignore

let searchTweets (query:string) =
    let batchSize = 200
    let rec pageSearch (maxId:int64 option) acc =
        let results =
            SearchTweetsParameters(query,
                SearchType = Nullable<_>(SearchResultType.Recent),
                MaximumNumberOfResults = batchSize,
                MaxId = (maxId |> Option.defaultValue -1L))
            |> Search.SearchTweets
            |> List.ofSeq
        if results.Length < batchSize
        then (results :: acc)
        else
            let oldestTweet = results |> Seq.minBy (fun x -> x.Id)
            pageSearch (Some(oldestTweet.Id-1L)) (results :: acc)
    pageSearch None []

let rec flatTweet (tweet:ITweet) =
    if tweet.IsRetweet
    then tweet.RetweetedTweet |> flatTweet
    else tweet

let oEmbed =
    // https://developer.twitter.com/en/docs/tweets/post-and-engage/api-reference/get-statuses-oembed
    let httpClient = new HttpClient()
    fun (tweet:ITweet) -> task {
        let url = sprintf "https://publish.twitter.com/oembed?url=%s&maxwidth=550&omit_script=true" tweet.Url
        let! resp = httpClient.GetAsync(url)
        let! str = resp.Content.ReadAsStringAsync()
        let json = JsonConvert.DeserializeObject<JObject>(str)
        return json.GetValue("html").ToObject<string>()
    }

type TweetType =
    | AllTweets
    | OnlyWithLinks
    | BeCareful

type NewsTweet = {
    Tweet: ITweet
    Query: string
    TweetType : TweetType
    Origin : string
}