module FSharp.Weekly.Tests.FsHeroes

open System.IO
open System.Threading.Tasks
open System.Net.Http
open NUnit.Framework
open SixLabors.ImageSharp
open SixLabors.ImageSharp.Processing

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
            "@7sharp9_"
            "@ScottWlaschin"
            "@sforkmann"
            "@tomaspetricek"
        ]
    ]

[<Test>]
let ``FsHeroes Images`` () =
    let client = FSharp.Weekly.Twitter.getClient()
    task {
        use httpClient = new HttpClient()
        let! bytes = httpClient.GetByteArrayAsync("https://www.nbc.com/sites/nbcunbc/files/files/images/2018/7/31/Heroes-KeyArt-Logo-Show-Tile-1920x1080.jpg")
        let baseImg = Image.Load bytes

        for year, users in heroes do
            let! images =
                users
                |> Seq.map (fun name ->
                    if name.StartsWith("@") then
                        task {
                            let! user = client.Users.GetUserAsync(name.TrimStart('@'))
                            use! stream = client.Users.GetProfileImageStreamAsync(user)
                            use ms = new MemoryStream()
                            stream.CopyTo(ms)
                            return ms.ToArray()
                        }
                    else
                        httpClient.GetByteArrayAsync(name)
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
            img.Save $"FsHeroes%s{year}.png"
     } :> Task

