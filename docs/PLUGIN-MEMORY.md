# Plug-in memory, processor and image size on a test Starboard

Written by `python3 tools/measure_plugins.py`. Measured on a test Starboard that holds made-up data, never on a real server. Memory is docker stats in MiB, idle after start and again after the screenshots used the plug-in; the cgroup column is memory.current for the same two moments. Processor is a percent of one core averaged over 60 seconds idle. Image size is the unpacked size in MB. Figures are summed over a plug-in's containers; a blank is a figure that could not be read.

| Plug-in | Containers | Memory at start (MiB) | Memory after use (MiB) | cgroup start / after use (MiB) | Processor (% of a core) | Image (MB) |
|---|---|---|---|---|---|---|
| audio-description | not measured yet | | | | | |
| audio-description-tracks | not measured yet | | | | | |
| backups-watch | not measured yet | | | | | |
| calibre-web | not measured yet | | | | | |
| checkrr | not measured yet | | | | | |
| direct-play | not measured yet | | | | | |
| disk-forecast | not measured yet | | | | | |
| dns-blocking | not measured yet | | | | | |
| download-summary | not measured yet | | | | | |
| home-assistant | not measured yet | | | | | |
| jellystat | not measured yet | | | | | |
| kavita | not measured yet | | | | | |
| library-cleanup | not measured yet | | | | | |
| library-health | not measured yet | | | | | |
| line-speed | not measured yet | | | | | |
| maintainerr | not measured yet | | | | | |
| most-watched | not measured yet | | | | | |
| navidrome | not measured yet | | | | | |
| notifications | not measured yet | | | | | |
| outside-services | not measured yet | | | | | |
| philips-hue | not measured yet | | | | | |
| picture-shrinker | not measured yet | | | | | |
| remote-access | not measured yet | | | | | |
| seerr | not measured yet | | | | | |
| styles | no container | | | | | |
| tdarr | not measured yet | | | | | |
| themearr | not measured yet | | | | | |
| tv-station | not measured yet | | | | | |
| uptime-kuma | not measured yet | | | | | |
| vpn-check | not measured yet | | | | | |
| watch-stats | not measured yet | | | | | |
| watching-now | not measured yet | | | | | |
| wizarr | not measured yet | | | | | |
