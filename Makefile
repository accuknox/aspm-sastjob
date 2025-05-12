REPO=accuknox
IMGNAME=sastjob
IMGTAG?=latest
IMGFULL=${REPO}/${IMGNAME}

docker-buildx:
	docker buildx build -f ./Dockerfile . \
		--platform linux/arm64,linux/amd64 \
		-t ${IMGFULL}:${IMGTAG} \
		-t ${IMGFULL}:latest \
		--push