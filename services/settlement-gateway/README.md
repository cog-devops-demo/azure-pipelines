# settlement-gateway

Nets a day's trades per counterparty and currency and emits the payment
instructions the downstream settlement systems consume.

## CI

There is no `azure-pipelines.yml` here. This service is built by
`settlement-gateway-classic`, a classic (designer) Azure DevOps build
definition: its steps, variables, and triggers live in the Azure DevOps
definition itself and can only be read through the ADO REST API
(`GET /_apis/build/definitions/{id}`), not from this repository.

The definition stamps a version and writes a build manifest from inline
PowerShell, installs dependencies, runs pytest, publishes the JUnit results,
packages the payload, records an artifact-registry receipt, and publishes
`settlement-gateway-drop`.
