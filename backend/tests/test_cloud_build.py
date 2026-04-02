import pytest
from unittest.mock import MagicMock, patch
from app.services.cloud_build import CloudBuildManager
import base64

@patch("google.cloud.devtools.cloudbuild_v1.CloudBuildClient")
def test_build_custom_image(mock_client_class):
    mock_client = mock_client_class.return_value
    mock_client.create_build.return_value.metadata.build.id = "build-123"
    
    manager = CloudBuildManager()
    image_tag, build_id = manager.build_custom_image("proj", "region", "user-1", "ws-name", "FROM base")
    
    assert "user-1-ws-name" in image_tag
    assert build_id == "build-123"
    assert mock_client.create_build.called
    
    args, kwargs = mock_client.create_build.call_args
    build = kwargs['request']['build']
    
    # Steps:
    # 0: echo chunk 1 > Dockerfile.base64
    # 1: base64 -d Dockerfile.base64 > Dockerfile
    # 2: docker build
    # 3: docker push
    assert len(build.steps) == 4
    assert "echo" in build.steps[0].args[1]
    assert "base64 -d" in build.steps[1].args[1]
    assert "build" in build.steps[2].args
    assert "push" in build.steps[3].args

@patch("google.cloud.devtools.cloudbuild_v1.CloudBuildClient")
def test_build_custom_image_large_dockerfile(mock_client_class):
    mock_client = mock_client_class.return_value
    mock_client.create_build.return_value.metadata.build.id = "build-large"
    
    manager = CloudBuildManager()
    
    # Create a large dockerfile (more than 8000 base64 chars)
    # 8000 base64 chars is about 6000 bytes.
    large_content = "RUN echo 'hello'\n" * 500
    
    image_tag, build_id = manager.build_custom_image("proj", "region", "user-1", "ws-large", large_content)
    
    args, kwargs = mock_client.create_build.call_args
    build = kwargs['request']['build']
    
    # Should have multiple echo steps (chunks)
    # len(large_content) is ~500 * 17 = 8500
    # base64 will be ~11333
    # With chunk_size=8000, we expect 2 chunks
    
    echo_steps = [s for s in build.steps if "echo" in s.args[1] and "Dockerfile.base64" in s.args[1]]
    assert len(echo_steps) >= 2
    assert "> Dockerfile.base64" in echo_steps[0].args[1]
    assert ">> Dockerfile.base64" in echo_steps[1].args[1]
