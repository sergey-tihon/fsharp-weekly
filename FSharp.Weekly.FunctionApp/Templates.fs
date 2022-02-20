module FSharp.Weekly.Templates

open System.Threading.Tasks
open FSharp.Control.Tasks
open Giraffe.ViewEngine
open Tweetinvi.Models

type TweetType =
    | AllTweets
    | OnlyWithLinks
    | BeCareful

type NewsTweet = {
    Tweet: ITweet
    Query: string
    TweetType : TweetType
    Origin : string
    IsDuplicate : bool
}

type ReportModel = {
    NewsTweets : NewsTweet list
    Logs: string list
    Links: (string*string) list
}

let formatTweet ind (newsTweet:NewsTweet) (formatter:ITweet->Task<string>) = task {
    let removeHref = $"javascript:remove('%s{newsTweet.Tweet.IdStr}')"
    let! formattedTweet = formatter newsTweet.Tweet
    return tr [_id newsTweet.Tweet.IdStr] [
        td [_style "min-width: 30px"] [
            p [_style "margin-top: 10px;"] [
                str <| "#"+ind.ToString()
            ]
        ]
        td [_style "min-width: 550px"] [
            rawText formattedTweet
        ]
        td [_style "padding-top: 10px; padding-bottom: 10px;"] [
            a [_class "button is-danger"; _href removeHref;
               _style "margin-bottom: 12px; margin-top: 10px;"] [
                str "Remove"
            ]
            div [_class "field is-grouped is-grouped-multiline"] [
                if newsTweet.IsDuplicate then
                    yield div [_class "control"] [
                        span [_class "tag is-warning"] [str "Duplicate"]
                    ]
                yield div [_class "control"] [
                    div [_class "tags has-addons"] [
                        yield span [_class "tag is-dark"] [str "query"]
                        let classStr =
                            match newsTweet.TweetType with
                            | AllTweets -> "is-success"
                            | OnlyWithLinks -> "is-link"
                            | BeCareful -> "is-warning"
                        yield span [_class ("tag "+classStr)] [
                            str newsTweet.Query
                        ]
                    ]
                ]
            ]
            div [_class "content is-small"] [
                yield h3 [] [ str "Links:" ]
                yield ul [] [
                    yield li [] [
                        a [_href newsTweet.Tweet.Url; _target "_blank"] [
                            str newsTweet.Tweet.Url
                        ]
                        str " (Tweet link)"
                    ]
                    for x in newsTweet.Tweet.Urls do
                        yield li [] [
                            a [_href x.URL; _target "_blank"] [
                                str x.ExpandedURL
                            ]
                        ]
                ]
                let lang = if newsTweet.Tweet.Language.HasValue then newsTweet.Tweet.Language.Value.ToString() else "English"
                if lang <> "English" then
                    yield h3 [] [str <| "Language: " + lang]
                yield h3 [] [str <| "Tweet Author: " + newsTweet.Tweet.CreatedBy.Name]
                if newsTweet.Origin <> newsTweet.Tweet.CreatedBy.Name then
                    yield h3 [] [str <| "Origin: " + newsTweet.Origin]
            ]
        ]
    ]
}

let report (model:ReportModel) formatter =  task {
    let cnt = List.length <| model.NewsTweets
    let! rows =
        model.NewsTweets
        |> List.mapi (fun i t -> formatTweet (cnt-i) t formatter)
        |> Task.WhenAll

    return html [] [
        head [] [
            meta [_charset "utf-8"]
            meta [_name "viewport"; _content "width=device-width, initial-scale=1"]
            title [] [str "F# Weekly Report"]
            link [_rel "stylesheet"; _type "text/css"; _href "https://cdnjs.cloudflare.com/ajax/libs/bulma/0.7.5/css/bulma.min.css"]
            script [_async; _src "https://platform.twitter.com/widgets.js"; _charset "utf-8"] []
            script [] [
                str "function remove(id){return (elem=document.getElementById(id)).parentNode.removeChild(elem);}"
            ]
            style [] [
                str "a:visited {color: burlywood;}"
            ]
        ]
        body [] [
            section [_class "section"] [
                table [_class "table is-striped is-hoverable is-fullwidth"]
                    (rows |> List.ofArray)
                div [_class "card"] [
                    header [_class "card-header"] [
                        p [_class "card-header-title"] [
                            str "Logs"
                        ]
                    ]
                    div [_class "card-content"] [
                        div [_class "content"] [
                            ul [] [
                                for line in model.Logs ->
                                    li [] [ str line ]
                            ]
                        ]
                    ]
                ]
                div [_class "card"] [
                    header [_class "card-header"] [
                        p [_class "card-header-title"] [
                            str "Links"
                        ]
                    ]
                    div [_class "card-content"] [
                        div [_class "content"] [
                            ul [] [
                                for (link, tweetLink) in model.Links ->
                                    li [] [
                                        str "["
                                        a [_href tweetLink; _target "_blank"] [ str "tweet" ]
                                        str "] "
                                        a [_href link; _target "_blank"] [ str link ]
                                    ]
                            ]
                        ]
                    ]
                ]
            ]
        ]
    ]
}
