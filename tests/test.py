from zoektpy import ZoektClient

# Create a client
client = ZoektClient(host="localhost", port=6070)

# Basic search
result = client.search("Kalash Pandey")

# Print matches
for file in result.Files:
    print(f"Found in {file.Repository}/{file.FileName}")
    
    for chunk in file.ChunkMatches or []:
        content = chunk.get_decoded_content()
        print(content)

# Close the client when done
client.close()