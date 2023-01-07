[<RequireQualifiedAccess>]
module FSharp.Weekly.Storage

open System
open System.IO
open System.Threading.Tasks
open Microsoft.Azure.Storage
open Microsoft.Azure.Storage.Blob

type IFileSaver = string -> string -> bool-> Task<bool>
type IStorage = string -> Task<IFileSaver>

let localStorage () :IStorage =
    let getOrCreateDir name root =
        let dir = Path.Combine(root, name)
        if not <| Directory.Exists(dir) then
            Directory.CreateDirectory(dir) |> ignore
        dir
    let root = Environment.CurrentDirectory |> getOrCreateDir "temp"

    fun containerName -> task {
        let container = root |> getOrCreateDir containerName
        return (fun fileName content isOverwrite -> task {
            let path = Path.Combine(container, fileName)
            let isExist = File.Exists path
            if (not isExist) || isOverwrite then
                do! File.WriteAllTextAsync(path, content)
                return true
            else return false
        })
    }

let cloudBlobStorage storageConnectionString  :IStorage =
    let client =
        let storageAccount = CloudStorageAccount.Parse(storageConnectionString)
        storageAccount.CreateCloudBlobClient()
    fun containerName -> task {
        let container = client.GetContainerReference(containerName)
        let! _ = container.CreateIfNotExistsAsync()
        return (fun fileName content isOverwrite -> task {
            let blockBlob = container.GetBlockBlobReference(fileName)
            let! isExist = blockBlob.ExistsAsync()
            if (not isExist) || isOverwrite then
                do! blockBlob.UploadTextAsync(content)
                return true
            else return false
        })
    }

open Microsoft.Azure.Cosmos.Table

type TweetRow (tweetId:int64, created:DateTime, userName:string, text:string, json:string) as this =
    inherit TableEntity()
    do
        this.PartitionKey <- created.Year.ToString()
        this.RowKey <- tweetId.ToString()
    new() = TweetRow(-1L, DateTime.MinValue, "", "", "{}")
    member val TweetId = tweetId with get, set
    member val CreatedDate = created with get, set
    member val UserScreenName = userName with get, set
    member val Text = text with get, set
    member val Json = json with get, set



let cloudTableStorage storageConnectionString =
    let client =
        let storageAccount = CloudStorageAccount.Parse(storageConnectionString)
        storageAccount.CreateCloudTableClient()
    fun tableName -> task {
        let table = client.GetTableReference(tableName)
        let! _ = table.CreateIfNotExistsAsync()
        return (fun (tweet:TweetRow) -> task {
            let retrieveOperation = TableOperation.Retrieve<TweetRow>(tweet.PartitionKey, tweet.RowKey)
            let! result = table.ExecuteAsync(retrieveOperation)
            if isNull result.Result
            then
                let insertOperation = TableOperation.Insert(tweet)
                let! _ = table.ExecuteAsync(insertOperation)
                return true
            else
                return false
        })
    }

let getEnvValue name =
    let value = Environment.GetEnvironmentVariable(name, EnvironmentVariableTarget.Process)
    if isNull value
    then failwithf $"Environment variable %s{name} is not defined"
    else value

let configuredBlobStorage() =
    let connectionString = getEnvValue "WEEKLY_STORAGE_CONNECTION_STRING"
    cloudBlobStorage connectionString

let configuredTableStorage() =
    let connectionString = getEnvValue "WEEKLY_STORAGE_CONNECTION_STRING"
    cloudTableStorage connectionString
