# Plug-in memory, processor and image size on a test Starboard

Written by `python3 tools/measure_plugins.py`. Measured on a test Starboard that holds made-up data, never on a real server. Memory is docker stats in MiB, idle after start and again after the screenshots used the plug-in; the cgroup column is memory.current for the same two moments. Processor is a percent of one core averaged over 60 seconds idle. Image size is the unpacked size in MB. Figures are summed over a plug-in's containers; a blank is a figure that could not be read.

| Plug-in | Containers | Memory at start (MiB) | Memory after use (MiB) | cgroup start / after use (MiB) | Processor (% of a core) | Image (MB) |
|---|---|---|---|---|---|---|
| audio-description | 1 | 12.2 | 12.9 | 12.6 / 12.9 | 0 | 61.6 |
| audio-description-tracks | 1 | 15.2 | 15.3 | 15.2 / 15.3 | 0 | 110.6 |
| backups-watch | did not run: Did not stay running on the test server (plugin-backups-watch-main stopped; exit 1, killed by memory limit: false) | | | | | |
| calibre-web | 1 | 144.4 | 177 | 146.4 / 178.4 | 0 | 754.7 |
| checkrr | did not run: Did not stay running on the test server (plugin-checkrr-main, plugin-checkrr-app stopped; exit 2, killed by memory limit: false) | | | | | |
| direct-play | 1 | 16 | 16 | 16 / 16 | 0 | 188.8 |
| disk-forecast | 1 | 13.3 | 13.7 | 13.3 / 13.7 | 0 | 61.6 |
| dns-blocking | 1 | 12.2 | 12.2 | 12.2 / 12.2 | 0 | 61.6 |
| download-summary | 1 | 13.2 | 13.4 | 13.2 / 13.4 | 0 | 61.6 |
| home-assistant | 1 | 12.2 | 12.2 | 12.2 / 12.2 | 0 | 61.6 |
| jellystat | did not run: Did not stay running on the test server (plugin-jellystat-main, plugin-jellystat-app, plugin-jellystat-db stopped; exit 1, killed by memory limit: false) | | | | | |
| kavita | did not run: Did not stay running on the test server (plugin-kavita-app stopped; exit 139, killed by memory limit: false) | | | | | |
| library-cleanup | 1 | 13.3 | 13.4 | 13.3 / 13.4 | 0 | 53.7 |
| library-health | 1 | 12.1 | 12.1 | 12.1 / 12.1 | 0 | 61.6 |
| line-speed | 1 | 12.1 | 12.1 | 12.1 / 12.1 | 0 | 61.6 |
| maintainerr | 1 | 191.6 | 195 | 199.7 / 214.3 | 0.4 | 423.7 |
| most-watched | 1 | 12.1 | 12.1 | 12.1 / 12.1 | 0 | 61.6 |
| navidrome | 1 | 19.8 | 13.8 | 17.5 / 18.4 | 0 | 238.4 |
| notifications | 1 | 12.3 | 12.3 | 12.3 / 12.3 | 0 | 61.6 |
| outside-services | 1 | 15.7 | 15.7 | 15.7 / 15.7 | 0 | 61.9 |
| philips-hue | 1 | 15.3 | 19.8 | 15.4 / 19.8 | 0 | 61.6 |
| picture-shrinker | 1 | 14.6 | 15.4 | 14.6 / 15.4 | 0 | 63.6 |
| remote-access | 1 | 17.3 | 17.3 | 17.3 / 17.3 | 0 | 168.4 |
| seerr | 1 | 236.2 | 228.6 | 244.3 / 274.5 | 0 | 479.9 |
| styles | no container | | | | | |
| tdarr | did not run: Did not stay running on the test server (plugin-tdarr-server stopped; exit 126, killed by memory limit: false) | | | | | |
| themearr | did not run: Did not stay running on the test server (plugin-themearr-main, plugin-themearr-app stopped; exit 2, killed by memory limit: false) | | | | | |
| tv-station | did not run: Did not stay running on the test server (plugin-tv-station-main stopped; exit 1, killed by memory limit: false) | | | | | |
| uptime-kuma | 1 | 218.1 | 220 | 249.3 / 248.8 | 0.1 | 1667.2 |
| vpn-check | 1 | 13.3 | 13.3 | 13.3 / 13.3 | 0 | 61.6 |
| watch-stats | 1 | 12.2 | 12.1 | 12.2 / 15.6 | 0 | 61.6 |
| watching-now | 1 | 12.9 | 13.2 | 12.9 / 13.2 | 0 | 61.6 |
| wizarr | did not run: Did not stay running on the test server (plugin-wizarr-app stopped; exit 1, killed by memory limit: false) | | | | | |
