# 

```bash
rm -f SQ-*.json # Remove existing reports
docker run --rm -it \
	-e SQ_URL=http://35.188.10.229:9000 \
	-e SQ_AUTH_TOKEN=<AUTH-TOKEN> \
	-e SQ_PROJECTS="^nimbus$" \
	-e SQ_ORG="accuknox" /* needed for sonarcloud.io */ \
	-e REPORT_PATH=/app/data/ \
	-v $PWD:/app/data/ \
	accuknox/sastjob:1.0.2
```

This will create a bunch of SQ-*.json files, one for every project/component found.

## Configuration

|      Var       | Sample Value              | Description                        |
|----------------|---------------------------|------------------------------------|
| SQ_URL*        | http://35.188.10.229:9000, https://sonarcloud.io/ | SonarQube server URL               |
| SQ_AUTH_TOKEN* | squ_token                 | SonarQube user authn token         |
| SQ_PROJECTS    | "^nimbus$"                | Scan the given projects/components |
| SQ_ORG    | "accuknox"                | Required in case of sonarcloud enterprise. |
| REPORT_PATH    | /app/data/                | Path to keep the report json files |

> variables marked with '*' are mandatory configuration options

## Upload reports to AccuKnox Management Portal

```bash
TENANT_ID=2509
LABEL=SAST
AK_URL="cspm.demo.accuknox.com"
AK_TOK=<artifact token received from accuknox management plane>

for file in `ls -1 SQ-*.json`; do
	curl --location "https://$AK_URL/api/v1/artifact/?tenant_id=$TENANT_ID&data_type=SQ&save_to_s3=True&label_id=$LABEL" \
		 --header "Tenant-Id: $TENANT_ID" \
		 --header "Authorization: Bearer $AK_TOK" \
		 --form "file=@"$file""
done
```
