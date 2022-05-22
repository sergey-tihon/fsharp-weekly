[<RequireQualifiedAccess>]
module FSharp.Weekly.Twitter

open System.Net.Http
open FSharp.Control.Tasks
open Newtonsoft.Json
open Newtonsoft.Json.Linq
open Tweetinvi
open Tweetinvi.Models

let getClient () =
    let consumerKey = Storage.getEnvValue "TWITTER_CONSUMER_KEY"
    let consumerSecret = Storage.getEnvValue "TWITTER_CONSUMER_SECRET"
    let userAccessToken = Storage.getEnvValue "TWITTER_ACCESS_TOKEN"
    let userAccessSecret = Storage.getEnvValue "TWITTER_ACCESS_SECRET"
    TwitterClient(consumerKey, consumerSecret, userAccessToken, userAccessSecret)

let searchTweets (client:TwitterClient) (query:string) =
    task {
        let searchIterator = client.Search.GetSearchTweetsIterator(query)
        let result = System.Collections.Generic.List<_>()
        while (not <| searchIterator.Completed) do
            let! searchPage = searchIterator.NextPageAsync()
            result.Add(searchPage |> List.ofSeq)
        return List.ofSeq result
    }
    |> Async.AwaitTask
    |> Async.RunSynchronously

let rec flatTweet (tweet:ITweet) =
    if tweet.IsRetweet
    then tweet.RetweetedTweet |> flatTweet
    else tweet

let oEmbed =
    // https://developer.twitter.com/en/docs/tweets/post-and-engage/api-reference/get-statuses-oembed
    let httpClient = new HttpClient()
    fun (tweet:ITweet) -> task {
        let url = $"https://publish.twitter.com/oembed?url=%s{tweet.Url}&maxwidth=550&omit_script=true"
        let! resp = httpClient.GetAsync(url)
        let! str = resp.Content.ReadAsStringAsync()
        let json = JsonConvert.DeserializeObject<JObject>(str)
        return json.GetValue("html").ToObject<string>()
    }
