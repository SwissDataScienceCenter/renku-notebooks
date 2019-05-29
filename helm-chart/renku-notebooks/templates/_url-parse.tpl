{{/* vim: set filetype=mustache: */}}

{{/*
Parse a URL (<scheme>://<host><path>?<params>). Because of limited regex support
in go templates (http://masterminds.github.io/sprig/strings.html) we use a combination 
of regexFind to find the first occurrence of a pattern and trimPrefix to strip the found
occurrence before applying the next regex.
*/}}

{{/* Apply a regexFind to the complete URL which is passed to the template as scope (.) */}}
{{- define "url.scheme" -}}
{{- regexFind "https?" . -}}
{{- end -}}

{{/* 
Trim the <sheme>:// from the URL and, then pipe the rest into a regexFind which matches 
everything up to the first forward slash.
*/}}
{{- define "url.host" -}}
{{- trimPrefix (printf "%s://" (include "url.scheme" .)) . | regexFind "[^/]+"}}
{{- end -}}

{{/* 
Trim the <sheme>:// from the URL and, then pipe the rest into a regexFind which matches 
everything up to the first forward slash.
*/}}
{{- define "url.origin" -}}
{{- printf "%s://%s" (include "url.scheme" .) (include "url.host" .) -}}
{{- end -}}

{{/* 
Trim the origin (<scheme>://<host>) from the URL, then pipe the rest into a regexFind which matches 
everything up to the question mark.
*/}}
{{- define "url.path" -}}
{{- trimPrefix (include "url.origin" .) . | regexFind "[^?]+" }}
{{- end -}} 