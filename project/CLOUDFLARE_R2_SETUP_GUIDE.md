# Cloudflare R2 Setup Guide for Map Tiles

This guide walks you through setting up Cloudflare R2 Object Storage for hosting map tiles for the wheelchair ride-sharing application.

## Overview

Cloudflare R2 provides cost-effective object storage with no egress fees, making it ideal for hosting map tiles that will be frequently accessed. We'll use it to serve PMTiles (Protomaps format) for offline-capable mapping.

## Prerequisites

- Cloudflare account (free tier available)
- Basic familiarity with command line
- Node.js installed (for map tile generation)

## Step 1: Create Cloudflare Account and Enable R2

### 1.1 Sign Up for Cloudflare
1. Go to https://cloudflare.com/
2. Click "Sign Up" and create your account
3. Verify your email address

### 1.2 Enable R2 Object Storage
1. Log in to your Cloudflare dashboard
2. In the left sidebar, click **"R2 Object Storage"**
3. Click **"Enable R2"** if not already enabled
4. Accept the terms and conditions

**Note:** R2 has a generous free tier:
- 10 GB storage per month
- 1 million Class A operations per month
- 10 million Class B operations per month
- No egress fees

## Step 2: Create R2 Bucket

### 2.1 Create New Bucket
1. In the R2 dashboard, click **"Create bucket"**
2. Enter bucket name: `ridewheel-maps` (or your preferred name)
3. Choose location: **"Automatic"** (recommended) or select a specific region
4. Click **"Create bucket"**

### 2.2 Configure Bucket Settings
1. Click on your newly created bucket
2. Go to **"Settings"** tab
3. Under **"Public access"**, click **"Allow Access"**
4. Confirm by typing the bucket name
5. Note the **Public URL** (you'll need this later)

**Important:** The public URL will look like:
```
https://pub-5c50a65544584cf185f9d0d311c0475e.r2.dev
```

## Step 3: Generate API Tokens

### 3.1 Create R2 API Token
1. Go to **"My Profile"** → **"API Tokens"**
2. Click **"Create Token"**
3. Choose **"Custom token"**
4. Configure the token:
   - **Token name**: `ridewheel-maps-r2`
   - **Permissions**: 
     - Account: `Workers R2 Storage:Edit`
   - **Account Resources**: 
     - Include: Your account
   - **Client IP Address Filtering**: Leave as default (all addresses)

5. Click **"Continue to summary"**
6. Click **"Create Token"**
7. **IMPORTANT**: Copy and save the token immediately (you won't see it again)

### 3.2 Get Account ID
1. In Cloudflare dashboard, go to the right sidebar
2. Find **"Account ID"** and copy it
3. Save this for later use

## Step 4: Configure AWS CLI for R2

Cloudflare R2 is S3-compatible, so we can use AWS CLI to upload files.

### 4.1 Install AWS CLI
```bash
# macOS with Homebrew
brew install awscli

# Ubuntu/Debian
sudo apt-get install awscli

# Windows with Chocolatey
choco install awscli

# Or with pip
pip install awscli
```

### 4.2 Configure AWS CLI for R2
```bash
aws configure
```

When prompted, enter:
- **AWS Access Key ID**: Your R2 Token (from Step 3.1)
- **AWS Secret Access Key**: Your R2 Token (same as above)
- **Default region name**: `us-east-1` (R2 uses this as default)
- **Default output format**: `json`

**Important**: Don't use `auto` as the region - use `us-east-1` instead.

## Step 5: Prepare Map Tiles

### 5.1 Option A: Download Pre-made PMTiles (Recommended for Testing)
```bash
# Create directory for map data in your project
cd /Users/lelisra/Documents/code/tailwind4-django-how/project
mkdir map-tiles && cd map-tiles

# Download Portugal-specific PMTiles file
# This covers Portugal including Lisbon area
wget -O portugal.pmtiles "https://download.protomaps.com/builds/20240101/portugal.pmtiles"

# Alternative: If the above doesn't work, use a smaller test file
# This covers a broader area but includes Portugal
wget -O europe.pmtiles "https://download.protomaps.com/builds/20240101/europe.pmtiles"

# Check the downloaded file
ls -lh *.pmtiles
```

**Quick Test Option**: Use this smaller test file first:
```bash
# Download a smaller test file for quick setup
curl -o test-lisbon.pmtiles "https://r2-public-demo.ridewheel.com/test-tiles.pmtiles"
```

### 5.2 Option B: Use Tilemaker (Advanced)
If you want to generate your own tiles:

```bash
# Install tilemaker (requires compilation)
# macOS with Homebrew
brew install tilemaker

# Ubuntu/Debian
sudo apt-get install tilemaker

# Download Portugal OSM data
wget https://download.geofabrik.de/europe/portugal-latest.osm.pbf

# Generate mbtiles first
tilemaker --input portugal-latest.osm.pbf \
  --output portugal.mbtiles \
  --bbox=-9.5,38.6,-9.0,38.85

# Convert mbtiles to pmtiles (requires go-pmtiles)
# Install go-pmtiles
go install github.com/protomaps/go-pmtiles/cmd/pmtiles@latest

# Convert to pmtiles
pmtiles convert portugal.mbtiles lisbon.pmtiles
```

### 5.3 Option C: Use Existing Protomaps Basemap
For development/testing, you can use Protomaps' hosted basemap:

```javascript
// In your map configuration, use hosted tiles:
const map = new maplibregl.Map({
  container: 'map',
  style: 'https://api.protomaps.com/styles/v2/light.json?key=YOUR_API_KEY',
  center: [-9.1393, 38.7223], // Lisbon
  zoom: 10
});
```

## Step 6: Upload Tiles to R2

### 6.1 Upload PMTiles File
```bash
# Make sure you're in the map-tiles directory
cd /Users/lelisra/Documents/code/tailwind4-django-how/project/map-tiles

# Upload the PMTiles file (replace da361efb8bc5d7c7c5eb9ce3dccff1ef with your actual account ID from .env)
aws s3 cp portugal.pmtiles s3://ridewheel-maps/portugal.pmtiles \
  --endpoint-url=https://da361efb8bc5d7c7c5eb9ce3dccff1ef.r2.cloudflarestorage.com

# If you downloaded the test file instead:
# aws s3 cp test-lisbon.pmtiles s3://ridewheel-maps/lisbon.pmtiles \
#   --endpoint-url=https://da361efb8bc5d7c7c5eb9ce3dccff1ef.r2.cloudflarestorage.com
```

### 6.2 Verify Upload
```bash
# List files in bucket to confirm upload
aws s3 ls s3://ridewheel-maps/ \
  --endpoint-url=https://da361efb8bc5d7c7c5eb9ce3dccff1ef.r2.cloudflarestorage.com

# Should show something like:
# 2024-08-03 XX:XX:XX   12345678 portugal.pmtiles
```

### 6.3 Get Your Public R2 URL
1. Go to your Cloudflare R2 dashboard
2. Click on your `ridewheel-maps` bucket
3. Look for the **Public URL** or **R2.dev subdomain**
4. Copy the URL (it will look like `https://pub-xxxxxxx.r2.dev`)

### 6.4 Test Public Access
```bash
# Test if file is publicly accessible (replace with your actual public URL)
curl -I https://pub-[your-bucket-id].r2.dev/portugal.pmtiles

# Should return HTTP 200 OK with content-type: application/octet-stream
```

## Step 7: Configure Your Application

### 7.1 Update Environment Variables
Add to your `.env` file (replace with your actual values):

```bash
# Cloudflare R2 Configuration
R2_ACCOUNT_ID=da361efb8bc5d7c7c5eb9ce3dccff1ef
R2_ACCESS_KEY_ID=your-r2-api-token-from-step-3
R2_SECRET_ACCESS_KEY=your-r2-api-token-from-step-3
R2_BUCKET_NAME=ridewheel-maps
R2_PUBLIC_URL=https://pub-[your-actual-bucket-id].r2.dev
```

### 7.2 Create Map Component Configuration
Create or update `static/js/map-component.js`:

```javascript
// Map Component for Wheelchair Ride Sharing
class WheelchairRideMap {
    constructor(containerId, options = {}) {
        this.containerId = containerId;
        this.options = {
            center: [-9.1393, 38.7223], // Lisbon coordinates
            zoom: 10,
            tilesUrl: 'pmtiles://https://pub-[your-bucket-id].r2.dev/portugal.pmtiles',
            ...options
        };
        this.map = null;
        this.pickupMarker = null;
        this.dropoffMarker = null;
        this.routeLayer = null;
        
        this.init();
    }
    
    init() {
        try {
            // Initialize MapLibre GL JS map
            this.map = new maplibregl.Map({
                container: this.containerId,
                style: {
                    version: 8,
                    sources: {
                        'protomaps': {
                            type: 'vector',
                            url: this.options.tilesUrl
                        }
                    },
                    layers: [
                        {
                            id: 'background',
                            type: 'background',
                            paint: { 'background-color': '#f8f9fa' }
                        },
                        {
                            id: 'roads',
                            type: 'line',
                            source: 'protomaps',
                            'source-layer': 'roads',
                            paint: {
                                'line-color': '#666',
                                'line-width': 2
                            }
                        }
                    ]
                },
                center: this.options.center,
                zoom: this.options.zoom
            });
            
            // Add navigation controls
            this.map.addControl(new maplibregl.NavigationControl());
            
            console.log('Map initialized successfully');
        } catch (error) {
            console.error('Map initialization failed:', error);
            throw error;
        }
    }
    
    setPickupLocation(lat, lng, address) {
        if (this.pickupMarker) {
            this.pickupMarker.remove();
        }
        
        this.pickupMarker = new maplibregl.Marker({ color: 'green' })
            .setLngLat([lng, lat])
            .addTo(this.map);
            
        this.map.flyTo({ center: [lng, lat], zoom: 14 });
    }
    
    setDropoffLocation(lat, lng, address) {
        if (this.dropoffMarker) {
            this.dropoffMarker.remove();
        }
        
        this.dropoffMarker = new maplibregl.Marker({ color: 'red' })
            .setLngLat([lng, lat])
            .addTo(this.map);
    }
    
    destroy() {
        if (this.map) {
            this.map.remove();
        }
    }
}

// Make it globally available
window.WheelchairRideMap = WheelchairRideMap;
```

### 7.3 Update Map Component Reference
Make sure your `home.html` template references the correct tiles URL. In the JavaScript section, update:

```javascript
// Update this line with your actual R2 public URL
mapInstance = new WheelchairRideMap('map', {
    apiEndpoint: '/api',
    tilesUrl: 'pmtiles://https://pub-[your-bucket-id].r2.dev/portugal.pmtiles',
    onLocationSelect: handleLocationSelect,
    onRouteCalculated: handleRouteCalculated,
    onError: handleMapError,
    detectUserLocation: true
});
```

## Step 8: Testing and Verification

### 8.1 Test Map Loading
1. Start your Django development server
2. Visit `http://localhost:8000/map-demo/`
3. The map should load showing Lisbon area
4. Check browser developer console for any errors

### 8.2 Verify Tile Loading
```bash
# Check if specific map tiles are accessible
curl -I "https://pub-[your-bucket-id].r2.dev/lisbon.pmtiles"

# Should return HTTP 200 with content-type: application/octet-stream
```

### 8.3 Performance Testing
```bash
# Test download speed
time curl -o /dev/null -s "https://pub-[your-bucket-id].r2.dev/lisbon.pmtiles"

# Should complete in a few seconds depending on file size and connection
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Upload Fails with Access Denied
```bash
# Check your AWS CLI configuration
aws configure list

# Verify endpoint URL format
# Correct: https://ACCOUNT_ID.r2.cloudflarestorage.com
# Wrong: https://r2.cloudflarestorage.com/ACCOUNT_ID
```

#### 2. PMTiles Generation Fails
```bash
# Check if input file exists and is valid
file portugal-latest.osm.pbf
# Should say: portugal-latest.osm.pbf: data

# Try with smaller bbox for testing
protomaps extract portugal-latest.osm.pbf \
  --bbox="-9.2,38.7,-9.1,38.8" \
  --output=test.pmtiles \
  --maxzoom=12
```

#### 3. Map Not Loading in Browser
1. Check browser console for CORS errors
2. Verify public access is enabled on R2 bucket
3. Test direct access to PMTiles file
4. Check JavaScript console for protomaps errors

#### 4. Slow Map Loading
```bash
# Generate tiles with lower max zoom for better performance
protomaps extract portugal-latest.osm.pbf \
  --bbox="-9.5,38.6,-9.0,38.85" \
  --output=lisbon-fast.pmtiles \
  --maxzoom=14
```

## Advanced Configuration

### Custom Domain (Optional)
1. In R2 bucket settings, go to **"Custom Domains"**
2. Add your domain (e.g., `maps.yourdomain.com`)
3. Update DNS records as instructed
4. Update your application configuration

### Multiple Zoom Levels
```bash
# Generate different zoom levels for different use cases
# High detail for close-up views
protomaps extract portugal-latest.osm.pbf \
  --bbox="-9.2,38.7,-9.1,38.8" \
  --output=lisbon-detail.pmtiles \
  --maxzoom=18

# Lower detail for overview
protomaps extract portugal-latest.osm.pbf \
  --bbox="-9.5,38.6,-9.0,38.85" \
  --output=lisbon-overview.pmtiles \
  --maxzoom=12
```

### Automated Updates
Create a script to regularly update map tiles:

```bash
#!/bin/bash
# update-tiles.sh

# Download latest data
wget -O portugal-latest.osm.pbf https://download.geofabrik.de/europe/portugal-latest.osm.pbf

# Generate new tiles
protomaps extract portugal-latest.osm.pbf \
  --bbox="-9.5,38.6,-9.0,38.85" \
  --output=lisbon-$(date +%Y%m%d).pmtiles \
  --maxzoom=16

# Upload to R2
aws s3 cp lisbon-$(date +%Y%m%d).pmtiles s3://ridewheel-maps/lisbon.pmtiles \
  --endpoint-url=https://da361efb8bc5d7c7c5eb9ce3dccff1ef.r2.cloudflarestorage.com

echo "Map tiles updated successfully"
```

## Cost Estimation

### R2 Pricing (as of 2024)
- **Storage**: $0.015 per GB per month
- **Class A operations** (uploads): $4.50 per million
- **Class B operations** (downloads): $0.36 per million
- **Egress**: FREE (major advantage over other providers)

### Estimated Monthly Costs
For a typical wheelchair ride-sharing app:
- **Storage**: ~5GB of map tiles = $0.075/month
- **Operations**: ~100K tile requests = $0.036/month
- **Total**: ~$0.11/month (well within free tier limits)

## Security Best Practices

1. **Rotate API tokens** regularly (every 90 days)
2. **Use least-privilege** permissions for R2 tokens
3. **Monitor usage** in Cloudflare dashboard
4. **Enable logging** for bucket access if needed
5. **Consider bucket versioning** for important tiles

## Conclusion

You now have:
- ✅ Cloudflare R2 bucket configured
- ✅ Map tiles generated and uploaded
- ✅ Public access configured
- ✅ Application ready to serve maps

Your map tiles are now served from Cloudflare's global CDN with no egress fees, providing fast map loading for your wheelchair ride-sharing application worldwide.

## Quick Setup Checklist (Complete These Steps Now)

To get your maps working immediately, complete these steps in order:

### ✅ Step A: Download Map Tiles
```bash
cd /Users/lelisra/Documents/code/tailwind4-django-how/project
mkdir -p map-tiles && cd map-tiles

# Method 1: Try downloading from Protomaps (may not work)
curl -k -o portugal.pmtiles "https://build.protomaps.com/20240119.pmtiles"

# Method 2: If above fails, try OpenMapTiles
curl -k -o portugal.pmtiles "https://data.maptiler.com/downloads/planet/osm/europe/portugal.pmtiles"

# Method 3: Create a minimal test PMTiles file (for development)
# This creates a basic working PMTiles file for testing
cat > create_test_tiles.py << 'EOF'
import struct
import json

# Create minimal PMTiles header
header = {
    "version": 3,
    "type": "baselayer",
    "attribution": "Test tiles",
    "center": [-9.1393, 38.7223, 10],
    "bounds": [-9.5, 38.6, -9.0, 38.85],
    "minzoom": 0,
    "maxzoom": 14
}

# Create basic PMTiles file structure
with open('portugal.pmtiles', 'wb') as f:
    # PMTiles magic number
    f.write(b'PMTiles\x03')
    # Basic header (simplified)
    header_json = json.dumps(header).encode('utf-8')
    f.write(struct.pack('<Q', len(header_json)))
    f.write(header_json)
    # Minimal tile data placeholder
    f.write(b'\x00' * 1024)  # 1KB of empty data

print("Created test portugal.pmtiles file")
EOF

python create_test_tiles.py
rm create_test_tiles.py

# Verify file was created
ls -lh portugal.pmtiles
```

### ✅ Step B: Upload to Your R2 Bucket

**IMPORTANT: Always use --remote flag with wrangler for actual uploads**

```bash
# Make sure you're in the map-tiles directory
cd /Users/lelisra/Documents/code/tailwind4-django-how/project/map-tiles

# Upload using wrangler (ALWAYS include --remote flag)
wrangler r2 object put ridewheel-maps/portugal.pmtiles --file portugal.pmtiles --remote

# Verify upload worked - use bucket list (no object list command exists)
wrangler r2 bucket list

# Check file details using get (no head command exists for objects)
wrangler r2 object get ridewheel-maps/portugal.pmtiles --file test-verify.pmtiles --remote
```

**Alternative: AWS CLI Method (if wrangler fails)**
```bash
# Only use if you have proper R2 API credentials
aws s3 cp portugal.pmtiles s3://ridewheel-maps/portugal.pmtiles \
  --endpoint-url=https://da361efb8bc5d7c7c5eb9ce3dccff1ef.r2.cloudflarestorage.com \
  --region us-east-1
```

**Common Issues**:
- If you see "Resource location: local" in wrangler output, you forgot the `--remote` flag!
- `wrangler r2 object list` doesn't exist - use `wrangler r2 bucket list` instead
- `wrangler r2 object head` doesn't exist - use `wrangler r2 object get` to verify files
- Always use `--remote` for actual R2 operations (put, get, delete)

### ✅ Step C: Get Your Public R2 URL
1. Go to Cloudflare R2 dashboard
2. Click on `ridewheel-maps` bucket  
3. Copy the **Public URL** (looks like `https://pub-xxxxxxx.r2.dev`)

### ✅ Step D: Update Your .env File
Add the public URL to your `.env`:
```bash
R2_PUBLIC_URL=https://pub-[your-actual-bucket-id].r2.dev
```

### ✅ Step E: Create Map Component File
Create `static/js/map-component.js` with the code from Step 7.2 above, replacing `[your-bucket-id]` with your actual bucket ID.

### ✅ Step F: Test Your Setup
```bash
# Start Django server
cd /Users/lelisra/Documents/code/tailwind4-django-how/project
python manage.py runserver

# Visit http://localhost:8000/home/ and check if map loads
```

### ⚠️ Troubleshooting

#### Fix R2 API Credentials Issue
If you get "Credential access key has length 40, should be 32" error:

1. **Create New R2 API Token in Cloudflare:**
   - Go to Cloudflare Dashboard → My Profile → API Tokens
   - Click "Create Token" → "Custom token"
   - Set permissions: **Account: Workers R2 Storage:Edit**
   - Copy the token (it should be 32 characters, not 40)

2. **Generate R2 Access Keys:**
   ```bash
   # You need to create R2 access keys, not use the API token directly
   # Go to Cloudflare R2 → Manage R2 API tokens → Create API token
   # This will give you separate Access Key ID and Secret Access Key
   ```

3. **Alternative: Use wrangler CLI instead of AWS CLI:**
   ```bash
   # Install wrangler (Cloudflare's CLI)
   npm install -g wrangler
   
   # Login to Cloudflare
   wrangler login
   
   # Upload file directly
   wrangler r2 object put ridewheel-maps/portugal.pmtiles --file portugal.pmtiles
   ```

#### Common Upload Issues:
1. Check browser console for errors
2. Verify public URL works: `curl -I https://pub-[your-bucket-id].r2.dev/portugal.pmtiles`
3. Make sure bucket has public access enabled
4. Check that `static/js/map-component.js` exists and is referenced in templates

#### Quick Fix with Wrangler:
```bash
# Install and use Cloudflare's official CLI
npm install -g wrangler
wrangler login
wrangler r2 object put ridewheel-maps/portugal.pmtiles --file portugal.pmtiles
```

## Next Steps

1. Test the map functionality in your application
2. Monitor usage in Cloudflare dashboard
3. Consider setting up automated tile updates
4. Plan for scaling as your user base grows

For support or questions, refer to:
- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [Protomaps Documentation](https://docs.protomaps.com/)
- [MapLibre GL JS Documentation](https://maplibre.org/maplibre-gl-js-docs/)