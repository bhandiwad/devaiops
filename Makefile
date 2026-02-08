.PHONY: beta-install beta-verify beta-demo beta-reset beta-release-checklist platform-test sdk

beta-install:
	./dev/beta-install.sh

beta-verify:
	./dev/beta-verify.sh

beta-demo:
	./dev/beta-demo.sh

beta-reset:
	./dev/beta-reset.sh

platform-test:
	cd services/platform-api && uv run pytest

sdk:
	cd services/platform-api && make sdk

beta-release-checklist: platform-test sdk beta-verify
	@echo "Beta release checklist complete"
