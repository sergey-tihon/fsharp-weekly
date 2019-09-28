module FSharp.Weekly.Tests.FsHeroes

open System.Threading.Tasks
open System.Net.Http
open FSharp.Control.Tasks
open NUnit.Framework
open Tweetinvi
open SixLabors.ImageSharp
open SixLabors.ImageSharp.Processing
open SixLabors.ImageSharp.Processing
open SixLabors.Primitives

let heroes =
    [
        "2019", [
            "@auduchinok"
            "@zaid_ajaj"
            "@evelgab"
            "@Tim_Lariviere"
            "@R0MMSEN"
        ]
        "2018", [
            "@MangelMaxime"
            "https://avatars1.githubusercontent.com/u/777696?s=460&v=4"
            "@dsyme"
            "@selketjah"
        ]
        "2017", [
            "@isaac_abraham"
            "@_cartermp"
            "@kot_2010"
            "@enricosada"
            "@TRikace"
        ]
        "2016", [
            "@alfonsogcnunez"
            "@k_cieslak"
            "@brandewinder"
            "@ReedCopsey"
            "@sergey_tihon"
        ]
        "2015", [
            "@lefthandedgoat"
            "@7sharp9_exhumed"
            "@ScottWlaschin"
            "@sforkmann"
            "@tomaspetricek"
        ]
    ]

[<Test>]
let ``FsHeroes Images`` () =
    FSharp.Weekly.Twitter.auth()
    task {
        use client = new HttpClient()
        let! bytes = client.GetByteArrayAsync("https://www.nbc.com/sites/nbcunbc/files/files/images/2018/7/31/Heroes-KeyArt-Logo-Show-Tile-1920x1080.jpg")
        let baseImg = Image.Load bytes

        for (year, users) in heroes do
            let! images =
                users
                |> Seq.map (fun name ->
                    if name.StartsWith("@") then
                        let x = User.GetUserFromScreenName(name.TrimStart('@'))
                        client.GetByteArrayAsync(x.ProfileImageUrl400x400)
                    else
                        client.GetByteArrayAsync(name)
                   )
                |> Task.WhenAll
            let img = baseImg.Clone(fun ctx ->
                let size = ctx.GetCurrentSize()
                let picWidth = (size.Width - 2*80 - 60) / images.Length
                images |> Seq.iteri (fun i bytes ->
                    let size = picWidth + 60
                    let resizeOptions = ResizeOptions(Size=Size(size, size), Mode = ResizeMode.Max)
                    let photo = Image.Load(bytes).Clone(fun ctx' -> ctx'.Resize(resizeOptions) |>  ignore)
                    let location = Point(80 + i*picWidth, 510)
                    ctx.DrawImage(photo, location, 1.0f) |> ignore
                )
            )
            img.Save(sprintf "FsHeroes%s.png" year)
     } :> Task

