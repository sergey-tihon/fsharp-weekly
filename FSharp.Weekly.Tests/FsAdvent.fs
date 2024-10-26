module FSharp.Weekly.Tests.FsAdvent

open System
open System.IO
open Giraffe.ViewEngine
open NUnit.Framework

let rowTemplate =
    let mutable ind = (DateTime.Now.Year % 100) * 100
    let primaryStyle = "color: #ff0000;";
    fun (date:DateTime) isPrimary ->
        ind <- ind + 1
        let index = str <| $"#%04d{ind}"
        tr [] [
            td [] [
                if isPrimary
                then span [_style primaryStyle] [index]
                else index
            ]
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
                yield rowTemplate date (date <= adventEnd)
                //if date <= adventEnd then
                //    yield rowTemplate date false
                date <- date + TimeSpan.FromDays(1.0)
        ]
    ]

[<Test>]
let ``FsAdvent 2024 table`` () =
    let adventStart = DateTime(2024, 12, 1)
    let adventEnd   = DateTime(2024, 12, 24)
    let lastPost    = DateTime(2025, 1, 1) + TimeSpan.FromHours(23.999)
    let htmlTable =
        template adventStart adventEnd lastPost
        |> RenderView.AsString.htmlDocument
    let content = htmlTable.Replace("</tr><","</tr>\n<").Replace("</td><","</td>\n<")
    let path = Path.Combine(Environment.CurrentDirectory, "FsAdvent.html")
    File.WriteAllText(path, content)
