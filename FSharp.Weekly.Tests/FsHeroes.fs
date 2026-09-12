module FSharp.Weekly.Tests.FsHeroes

open System.IO
open System.Threading.Tasks
open System.Net.Http
open NUnit.Framework
open SkiaSharp

let heroes =
    [ "2019", [ "@auduchinok"; "@zaid_ajaj"; "@evelgab"; "@Tim_Lariviere"; "@R0MMSEN" ]
      "2018",
      [ "@MangelMaxime"
        "https://avatars1.githubusercontent.com/u/777696?s=460&v=4"
        "@dsyme"
        "@selketjah" ]
      "2017", [ "@isaac_abraham"; "@_cartermp"; "@kot_2010"; "@enricosada"; "@TRikace" ]
      "2016",
      [ "@alfonsogcnunez"
        "@k_cieslak"
        "@brandewinder"
        "@ReedCopsey"
        "@sergey_tihon" ]
      "2015",
      [ "@lefthandedgoat"
        "@7sharp9_"
        "@ScottWlaschin"
        "@sforkmann"
        "@tomaspetricek" ] ]

[<Test>]
let ``FsHeroes Images`` () =
    let client = FSharp.Weekly.Twitter.getClient ()
    task {
        use httpClient = new HttpClient()
        let! bytes =
            httpClient.GetByteArrayAsync("https://www.nbc.com/sites/nbcunbc/files/files/images/2018/7/31/Heroes-KeyArt-Logo-Show-Tile-1920x1080.jpg")
        use baseImg = SKBitmap.Decode bytes

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
            use img = baseImg.Copy()
            use canvas = new SKCanvas(img)
            let picWidth = (img.Width - 2 * 80 - 60) / images.Length

            images
            |> Seq.iteri (fun i bytes ->
                use photo = SKBitmap.Decode bytes
                let targetSize = picWidth + 60
                let scale =
                    min (float targetSize / float photo.Width) (float targetSize / float photo.Height)
                let width = int (float photo.Width * scale)
                let height = int (float photo.Height * scale)
                let left = 80 + i * picWidth
                let destination =
                    SKRect(float32 left, 510f, float32 (left + width), float32 (510 + height))
                canvas.DrawBitmap(photo, destination, SKSamplingOptions(SKFilterMode.Linear, SKMipmapMode.None))
            )

            use image = SKImage.FromBitmap(img)
            use encoded = image.Encode(SKEncodedImageFormat.Png, 100)
            use output = File.OpenWrite($"FsHeroes%s{year}.png")
            encoded.SaveTo(output)
    }
    :> Task
