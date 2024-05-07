{{/*
Expand the name of the chart.
*/}}
{{- define "chart.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "chart.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "chart.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "chart.labels" -}}
helm.sh/chart: {{ include "chart.chart" . }}
{{ include "chart.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "chart.selectorLabels" -}}
app.kubernetes.io/name: {{ include "chart.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Generate s3 configuration */}}
{{- define "chart.s3config" -}}
spark.hadoop.fs.s3a.endpoint: {{ .Values.s3.endpoint }}
spark.hadoop.fs.s3a.access.key: {{ .Values.s3.access_key }}
spark.hadoop.fs.s3a.secret.key: {{ .Values.s3.secret_key }}
spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version: "2"
spark.hadoop.fs.s3a.connection.ssl.enabled: {{ .Values.s3.use_ssl }}
spark.hadoop.fs.s3a.fast.upload: "true"
spark.hadoop.fs.s3a.path.style.access: "true"
spark.hadoop.fs.s3a.aws.credentials.provider: "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider"
spark.hadoop.fs.s3a.impl: "org.apache.hadoop.fs.s3a.S3AFileSystem"
{{- end }}


{{/* Generate common configuration */}}
{{- define "chart.common" -}}
type: Python
pythonVersion: "3"
mode: cluster
image: "{{ .Values.image.repository }}/{{ .Values.image.name }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
imagePullPolicy: "{{ .Values.image.pullPolicy}}"
sparkVersion: "3.4.1"
restartPolicy:
  type: OnFailure
  onFailureRetries: 3
  onFailureRetryInterval: 10
  onSubmissionFailureRetries: 5
  onSubmissionFailureRetryInterval: 20
{{- end }}