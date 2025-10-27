import requests
import json
import os
import subprocess

OM_TARGET_URL = os.getenv('OM_TARGET_URL', 'https://api.omarchysandbox.com')
OM_API_TOKEN = os.getenv('OM_API_TOKEN')
DEPLOYMENT_FILE = 'PlatformSpec.jsonld'

def gitops_deploy():
  # 1. Prepare your deployment config
  if not os.path.exists(DEPLOYMENT_FILE):
    # Get a minimal spec to run
    subprocess.run([
      'curl',
      '-fsSL',
      'https://raw.githubusercontent.com/omarchy/template/main/template.jsonld',
      '-o', DEPLOYMENT_FILE
    ])

  # 2. Om CLI Install (if not present)
  if not os.path.exists('/usr/local/bin/om'):
    subprocess.run([
      'bash', '-c',
      '''
        curl -fsSL https://github.com/omarchy/cli/releases/latest/download/om_linux_amd64 > om &&
        chmod +x om &&
        mv om /usr/local/bin
      ''',
    ])

  # 3. Deployment Command
  cmd = [
      'om',
      'apply',
      '-e', OM_TARGET_URL,
      '--auth-type', 'basic',
      '--api-token', OM_API_TOKEN,
      'configs/ai-token.jsonld'
  ]

  result = subprocess.run(cmd, capture_output=True, text=True)
  print(result.stdout)
  if result.returncode != 0:
    raise Exception(f"GitOps failed:\n{result.stderr}")
