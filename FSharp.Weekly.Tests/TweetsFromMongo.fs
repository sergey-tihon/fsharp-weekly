module FSharp.Weekly.Tests.TweetsFromMongo

open System
open MongoDB.Bson
open MongoDB.Driver
open System.Threading.Tasks
open FSharp.Control.Tasks
open FSharp.Weekly
open NUnit.Framework

[<Test>]
let ``from Mongo to Azure Table`` () =
    let mongoUrl = MongoUrl("mongodb://127.0.0.1:27017/fsharp")
    let client = MongoClient(mongoUrl)
    let database = client.GetDatabase(mongoUrl.DatabaseName)
    let collection = database.GetCollection<BsonDocument>("fsharp")

    let items = collection.Find(Builders.Filter.Empty).ToEnumerable()

    task {
        let storage = Storage.configuredTableStorage()
        let! saveTweet = storage "fsharptweets"

        let! saveResults =
            items
            |> Seq.map (fun x -> task {
                let (_,tweetId) = x.TryGetValue("TweetId")
                let (_,created) = x.TryGetValue("CreatedDate")
                let (_,author) = x.TryGetValue("FromUserScreenName")
                let (_,text) = x.TryGetValue("Text")

                let tweetId = tweetId.AsString |> Int64.Parse
                let created = created.AsBsonDateTime.ToUniversalTime()
                let author = author.AsString
                let text = text.AsString
                let json = x.ToJson()

                let tweet = Storage.TweetRow(tweetId, created, author, text, json)
                return! saveTweet tweet
              })
            |> Task.WhenAll

        let savedItems = saveResults |> Seq.filter id |> Seq.length
        printfn $"Saved %d{savedItems} new tweets in Table Storage"
    } :> Task
