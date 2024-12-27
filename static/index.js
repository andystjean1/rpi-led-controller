async function triggerEndpoint(endpoint, data = null) {
    try {
        const options = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        };
        const response = await fetch(endpoint, options);
        const result = await response.json();
        console.log(result);
    } catch (error) {
        alert('Error: Unable to trigger the endpoint');
        console.error(error);
    }
}