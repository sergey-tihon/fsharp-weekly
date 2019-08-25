module FSharp.Weekly.Storage

open System
open System.IO
open System.Threading.Tasks
open FSharp.Control.Tasks
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

let getEnvValue name =
    let value = System.Environment.GetEnvironmentVariable(name, System.EnvironmentVariableTarget.Process)
    if isNull value
    then failwithf "Environment variable %s is not defined" name
    else value

let configuredBlobStorage() =
     let connectionString = getEnvValue "WEEKLY_STORAGE_CONNECTION_STRING"
     cloudBlobStorage connectionString