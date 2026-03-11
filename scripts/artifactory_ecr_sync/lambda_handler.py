import base64
import json
import logging
import os
from typing import Dict, Optional

import boto3
import requests
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

required_env_vars = [
    'CREDENTIALS_SECRET_ARN',
    'ARTIFACTORY_URL', 
    'ARTIFACTORY_REPO',
    'ECR_REGION',
    'ECR_REGISTRY'
]

for var in required_env_vars:
    if not os.environ.get(var):
        raise ValueError(f"Required environment variable {var} is not set")

ecr_client = boto3.client('ecr', region_name=os.environ['ECR_REGION'])
secrets_client = boto3.client('secretsmanager')

def get_artifactory_credentials() -> Dict[str, str]:
    """Retrieve Artifactory credentials from AWS Secrets Manager"""
    secret_arn = os.environ['CREDENTIALS_SECRET_ARN']
    
    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        credentials = json.loads(response['SecretString'])
        
        return {
            'username': credentials.get('username'),
            'tokenId': credentials.get('tokenId'),
            'tokenSecret': credentials.get('tokenSecret')
        }
    except ClientError as e:
        logger.error(f"Error retrieving credentials: {e.response['Error']['Code']}")
        raise
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Error processing credentials: {e}")
        raise

def get_manifest(registry_url: str, repo: str, image: str, tag: str, auth: tuple) -> Optional[Dict]:
    """Get image manifest from Artifactory"""
    manifest_url = f"{registry_url}/api/docker/{repo}/v2/{image}/manifests/{tag}"
    headers = {'Accept': 'application/vnd.docker.distribution.manifest.v2+json'}
    
    try:
        response = requests.get(manifest_url, auth=auth, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to get manifest for {image}:{tag}: {e}")
        return None

def get_blob(registry_url: str, repo: str, image: str, digest: str, auth: tuple) -> Optional[bytes]:
    """Get image blob from Artifactory"""
    blob_url = f"{registry_url}/api/docker/{repo}/v2/{image}/blobs/{digest}"
    
    try:
        response = requests.get(blob_url, auth=auth, stream=True)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        logger.error(f"Failed to get blob {digest}: {e}")
        return None

def put_image_to_ecr(repo_name: str, image_tag: str, manifest: Dict, config_blob: bytes, layer_blobs: list) -> bool:
    """Push image to ECR using batch operations"""
    try:
        # Upload config blob
        config_digest = manifest['config']['digest']
        ecr_client.put_image(
            repositoryName=repo_name,
            imageManifest=json.dumps(manifest),
            imageTag=image_tag
        )
        logger.info(f"Successfully pushed {repo_name}:{image_tag} to ECR")
        return True
    except ClientError as e:
        logger.error(f"Failed to push image to ECR: {e.response['Error']['Code']}")
        return False

def sync_image(artifactory_url: str, artifactory_repo: str, image_name: str, tag: str, 
               artifactory_auth: tuple, ecr_registry: str) -> bool:
    """Sync image from Artifactory to ECR using registry APIs"""
    try:
        logger.info(f"Syncing {image_name}:{tag}")
        
        # Get manifest from Artifactory
        manifest = get_manifest(artifactory_url, artifactory_repo, image_name, tag, artifactory_auth)
        if not manifest:
            return False
        
        # Ensure ECR repository exists
        try:
            ecr_client.describe_repositories(repositoryNames=[image_name])
        except ClientError as e:
            if e.response['Error']['Code'] == 'RepositoryNotFoundException':
                logger.info(f"Creating ECR repository: {image_name}")
                ecr_client.create_repository(repositoryName=image_name)
            else:
                raise
        
        # Get config blob
        config_digest = manifest['config']['digest']
        config_blob = get_blob(artifactory_url, artifactory_repo, image_name, config_digest, artifactory_auth)
        if not config_blob:
            return False
        
        # Get layer blobs
        layer_blobs = []
        for layer in manifest.get('layers', []):
            blob = get_blob(artifactory_url, artifactory_repo, image_name, layer['digest'], artifactory_auth)
            if not blob:
                return False
            layer_blobs.append(blob)
        
        # Push to ECR
        return put_image_to_ecr(image_name, tag, manifest, config_blob, layer_blobs)
        
    except Exception as e:
        logger.error(f"Error syncing {image_name}:{tag}: {e}")
        return False

def lambda_handler(event, context):
    """AWS Lambda handler for syncing images from Artifactory to ECR"""
    
    try:
        artifactory_url = os.environ['ARTIFACTORY_URL'].rstrip('/')
        credentials = get_artifactory_credentials()
        artifactory_auth = (credentials['username'], credentials['tokenSecret'])
        artifactory_repo = event.get('artifactory_repo') or os.environ['ARTIFACTORY_REPO']
        ecr_registry = os.environ['ECR_REGISTRY'].rstrip('/')
        
        image_filters = (event.get('image_filters') or os.environ.get('IMAGE_FILTERS', '')).split(',') if os.environ.get('IMAGE_FILTERS') else None
        tag_filters = (event.get('tag_filters') or os.environ.get('TAG_FILTERS', '')).split(',') if os.environ.get('TAG_FILTERS') else None
        
        # Get images from Artifactory
        catalog_url = f"{artifactory_url}/api/docker/{artifactory_repo}/v2/_catalog"
        response = requests.get(catalog_url, auth=artifactory_auth)
        response.raise_for_status()
        images = response.json().get('repositories', [])
        
        successful_syncs = []
        failed_syncs = []
        
        for image_name in images:
            if image_filters and not any(f in image_name for f in image_filters if f):
                continue
                
            tags_url = f"{artifactory_url}/api/docker/{artifactory_repo}/v2/{image_name}/tags/list"
            response = requests.get(tags_url, auth=artifactory_auth)
            response.raise_for_status()
            tags = response.json().get('tags', [])
            
            for tag in tags:
                if tag_filters and not any(f in tag for f in tag_filters if f):
                    continue
                
                if sync_image(artifactory_url, artifactory_repo, image_name, tag, artifactory_auth, ecr_registry):
                    successful_syncs.append(f"{image_name}:{tag}")
                else:
                    failed_syncs.append(f"{image_name}:{tag}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Synced {len(successful_syncs)} images, {len(failed_syncs)} failed',
                'successful': successful_syncs,
                'failed': failed_syncs
            })
        }
        
    except requests.RequestException as e:
        logger.error(f"Artifactory API error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Artifactory API error'})
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }