.ONESHERLL:


# INFO:
# $@ - target prerequisit
# $(word n,$^) - n-th prerequisit in all ($^) prerequisites


PIP = venv/bin/pip
PYTHON = venv/bin/python
package = isacbot
INSTANCE_VOLUME = /usr/src/$(package)/instance
VERSION = $(shell sed -n 's/^.*version = "\(.\..\..\)"/\1/p' pyproject.toml)
# Assign this target-specific variable to solve the problem with PYTHONPATH
# and absolute imports in the src-layout project at all launch points.
# [see also](https://www.gnu.org/software/make/manual/html_node/Target_002dspecific.html)
run: export PYTHONPATH = $(CURDIR)/src


venv/bin/activate:
	@python -m venv venv
	@chmod +x $@
	@. ./$@
	@$(PIP) install --upgrade pip
ifneq ("$(wildcard ./requirements.txt)", "")
	@$(PIP) install --require-hashes --no-deps --only-binary :all: -r requirements.txt
endif
ifneq ("$(wildcard ./requirements-dev.txt)", "")
	@$(PIP) install --require-hashes --no-deps --only-binary :all: -r requirements-dev.txt
endif
venv: venv/bin/activate
	@. ./$<


run: src/$(package) venv
	@$(PYTHON) $</__main__.py


# Dependency managment with pip-tools.
venv/bin/pip-compile venv/bin/pip-sync: venv
	@$(PIP) install --only-binary :all: pip-tools
# Generate requirements.txt.
requirements.txt: venv/bin/pip-compile requirements.in
	@$< --no-strip-extras --generate-hashes --output-file=$@ $(word 2,$^)
	@echo $@ successfully created
# Generate requirements-dev.txt with constraints in requirements.txt.
requirements-dev.txt: venv/bin/pip-compile requirements.txt requirements-dev.in
	@$< --constraint=$(word 2,$^) --no-strip-extras --generate-hashes --output-file=$@ $(word 3,$^)
	@echo $@ successfully created
# Update packages in pip list by only requirements.txt.
.PHONY: pip-sync
pip-sync: venv/bin/pip-sync requirements.txt
	@$<
# Update packages in pip list by all requirements.
.PHONY: pip-sync-all
pip-sync-all: venv/bin/pip-sync requirements.txt requirements-dev.txt
	@$< $(word 2,$^) $(word 3,$^)
.PHONY: pip-upgrade-all
# Upgrade all dependencies versions, regenerate hashes.
pip-upgrade-all: venv/bin/pip-compile requirements.in requirements-dev.in
	@$< --upgrade --no-strip-extras --generate-hashes --output-file=requirements.txt $(word 2,$^)
	@$< --upgrade --constraint=requirements.txt --no-strip-extras --generate-hashes --output-file=requirements-dev.txt $(word 3,$^)
	@echo everything successfully upgraded and up-to-date

# Internationalization.
# Thx to https://github.com/lleballex/aiogram-template.
# --no-location argment for pybabel disable comments with location code in .pot file
i18n-extract: src/$(package) venv/bin/pybabel
	@$(word 2,$^) extract \
	--keywords=N_ \
	--no-location \
	--msgid-bugs-address="pan.vlados.w@gmail.com" \
	--copyright-holder="Vladislav Anisimov" \
	--project=$(package) \
	--version=$(VERSION) \
	--input-dirs=$< \
	-o $</locales/messages.pot\

i18n-init: src/$(package)/locales/messages.pot venv/bin/pybabel
	@$(word 2,$^) init -i $< -d $(shell dirname $<) -D messages -l en
	@$(word 2,$^) init -i $< -d $(shell dirname $<) -D messages -l ru

i18n-compile: src/$(package)/locales venv/bin/pybabel
	@$(word 2,$^) compile -d $< -D messages

i18n-update: src/$(package)/locales venv/bin/pybabel
	@make i18n-extract
	@$(word 2,$^) update -d $< -D messages -i $</messages.pot
	@echo WARNING: Write translations in $</*.po. Continue? [Y/n]
	@read line; if [ $$line = "n" ]; then echo Aborting...; exit 1 ; fi
	@make i18n-compile


docker-build: .python-version .dockerignore
	@docker build \
	--platform=linux/amd64 \
	--build-arg PYTHON_VERSION=$(shell cat $<) \
	--build-arg INSTANCE_VOLUME=$(INSTANCE_VOLUME) \
	-t $(package)_image .
docker-run: src/$(package)/config/.env.prd
	@docker run -d \
	-it \
	--platform=linux/amd64 \
	--env-file $< \
	--restart=unless-stopped \
	--memory="512m" \
	--cpus="1" \
	--name $(package)_container \
	--volume instance:$(INSTANCE_VOLUME) \
	$(package)_image
docker-stop:
	@docker stop $(package)_container
docker-attach:
	@docker attach $(package)_container
docker-remove:
	@docker rm $(package)_container
docker-debug:
	@docker run -it --name $(package)_container $(package)_image bash
docker-list-container-env:
	@docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' $(package)_container
docker-list-image-env:
	@docker inspect --format='{{range .Config.Env}}{{println .}}{{end}}' $(package)_image


clean:
	@find . -name __pycache__ -exec rm -rf {} +
	@find src/$(package)/locales -name messages.mo -exec rm -rf {} +
	@rm -rf src/$(package).egg-info
	@rm -rf dist
clean-all:
	@make clean
	@rm -rf venv