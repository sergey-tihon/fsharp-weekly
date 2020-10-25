module FSharp.Weekly.Tests.FsAdvent

open System
open System.IO
open Giraffe.GiraffeViewEngine
open NUnit.Framework

let rowTemplate =
    let mutable ind = (DateTime.Now.Year % 100) * 100
    fun (date:DateTime) ->
        ind <- ind + 1
        tr [] [
            td [] [ str <| sprintf "#%04d" ind]
            td [] [ str <| date.ToString("MMM dd (ddd)") ]
            td [] []
            td [] []
        ]

let template (adventStart:DateTime) (adventEnd:DateTime) (lastPost:DateTime) =
    table [_border "1"] [
        thead [] [
            tr [] [
                th [] [str "ID"]
                th [] [str "Date"]
                th [] [str "Author"]
                th [] [str "Post Title"]
            ]
        ]
        tbody [] [
            let mutable date = adventStart
            while date <= lastPost do
                yield rowTemplate date
                if date <= adventEnd then
                    yield rowTemplate date
                date <- date + TimeSpan.FromDays(1.0)
        ]
    ]

[<Test>]
let ``FsAdvent 2020 table`` () =
    let adventStart = DateTime(2020, 11, 29)
    let adventEnd   = DateTime(2020, 12, 24)
    let lastPost    = DateTime(2021, 1, 1)+TimeSpan.FromHours(23.999)
    let htmlTable =
        template adventStart adventEnd lastPost
        |> renderHtmlNode
    let content =htmlTable.Replace("</tr><","</tr>\n<").Replace("</td><","</td>\n<")
    let path = Path.Combine(Environment.CurrentDirectory, "FsAdvent.html")
    File.WriteAllText(path, content)
