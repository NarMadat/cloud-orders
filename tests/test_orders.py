def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs_url" in data


def test_app_info(client):
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert data["app_name"] == "cloud-orders-api"
    assert "hostname" in data
    assert "features" in data


def test_health_live(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or "process_cpu_seconds_total" in response.text or response.status_code == 200


def test_create_order(client):
    payload = {
        "customer_name": "Alice Smith",
        "customer_email": "alice@example.com",
        "item_name": "Kubernetes in Action Book",
        "quantity": 2,
        "unit_price": 39.99
    }
    response = client.post("/api/v1/orders", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["customer_name"] == "Alice Smith"
    assert data["total_price"] == 79.98
    assert data["status"] == "pending"


def test_get_order(client):
    # Create first
    create_res = client.post("/api/v1/orders", json={
        "customer_name": "Bob Marley",
        "customer_email": "bob@example.com",
        "item_name": "Terraform Up & Running",
        "quantity": 1,
        "unit_price": 45.00
    })
    order_id = create_res.json()["id"]

    # Fetch
    get_res = client.get(f"/api/v1/orders/{order_id}")
    assert get_res.status_code == 200
    assert get_res.json()["item_name"] == "Terraform Up & Running"


def test_list_orders(client):
    response = client.get("/api/v1/orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_update_order(client):
    create_res = client.post("/api/v1/orders", json={
        "customer_name": "Charlie",
        "customer_email": "charlie@example.com",
        "item_name": "Ansible for DevOps",
        "quantity": 1,
        "unit_price": 25.00
    })
    order_id = create_res.json()["id"]

    update_res = client.patch(f"/api/v1/orders/{order_id}", json={
        "status": "shipped",
        "quantity": 3
    })
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["status"] == "shipped"
    assert data["quantity"] == 3
    assert data["total_price"] == 75.00


def test_delete_order(client):
    create_res = client.post("/api/v1/orders", json={
        "customer_name": "Dave",
        "customer_email": "dave@example.com",
        "item_name": "Docker Deep Dive",
        "quantity": 1,
        "unit_price": 20.00
    })
    order_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/orders/{order_id}")
    assert del_res.status_code == 204

    # Verify deleted
    get_res = client.get(f"/api/v1/orders/{order_id}")
    assert get_res.status_code == 404
