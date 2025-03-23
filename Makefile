REPO=accuknox
IMGNAME=sastjob
IMGTAG?=latest

docker-buildx:
	docker buildx build -f ./Dockerfile . --platform linux/arm64,linux/amd64 \
	-t ${REPO}/${IMGNAME}:${IMGTAG} \
	-t ${REPO}/${IMGNAME}:latest \
	--push
