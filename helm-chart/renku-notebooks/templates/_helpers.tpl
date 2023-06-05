{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "notebooks.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "notebooks.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "notebooks.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Define http scheme
*/}}
{{- define "notebooks.http" -}}
{{- if .Values.global.useHTTPS -}}
https
{{- else -}}
http
{{- end -}}
{{- end -}}

{{/*
Renku crac service URL, determine if the chart is deployed standalone or part of Renku
based on the number of dependencies. At most the notebooks helm chart has 3 dependencies
but the Renku helm chart has many more. So we use this to determine which named template to use
to get the right name of the crac service which is defined in the parent chart.
*/}}
{{- define "notebooks.cracUrl" -}}
{{- if le (len .Chart.Dependencies) 3 -}}
{{ printf "http://%s-crac/api/data" (include "notebooks.fullname" .) }}
{{- else -}}
{{ printf "http://%s-crac/api/data" (include "renku.fullname" .) }}
{{- end -}}
{{- end -}}
