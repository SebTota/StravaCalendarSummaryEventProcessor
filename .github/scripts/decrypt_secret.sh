 #!/bin/sh
gpg --quiet --batch --yes --decrypt --passphrase="$SECRET_PASSPHRASE" \
--output .github/scripts/secrets.yaml .github/scripts/secrets.yaml.gpg
