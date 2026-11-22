/* Original pilot firmware for this thesis. ESP-IDF v5.4.3 / ESP32-S3 only.
 * Radio APIs follow Espressif's public headers; no private CSI payload offsets.
 * This source still requires a physical three-board pilot before deployment.
 */
#include <inttypes.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "esp_event.h"
#include "esp_idf_version.h"
#include "esp_netif.h"
#include "esp_now.h"
#include "esp_random.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

#if ESP_IDF_VERSION != ESP_IDF_VERSION_VAL(5, 4, 3)
#error "Pilot firmware is pinned to ESP-IDF v5.4.3. Review APIs before upgrading."
#endif
#if !CONFIG_IDF_TARGET_ESP32S3
#error "Only ESP32-S3 has been targeted by this firmware."
#endif

#define MAGIC UINT32_C(0x31495343)
#define MAX_CSI_BYTES 640
#ifndef CONFIG_CSI_ROLE_TX
static const uint8_t TX_MAC[6] = {0x02, 0, 0, 0, 0, 1};
#else
static const uint8_t BROADCAST[6] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};
#endif
static uint32_t boot_id;

typedef struct __attribute__((packed)) {
    uint32_t magic, boot_id, sequence, reserved;
    uint64_t tx_us;
} probe_t;
_Static_assert(sizeof(probe_t) == 24, "Wire payload changed");

#ifndef CONFIG_CSI_ROLE_TX
typedef struct {
    bool marker;
    uint32_t device_us;
    uint16_t rx_seq, len;
    bool first_word_invalid;
    int rssi, channel, sig_mode, mcs, cwb, rx_state;
    probe_t probe;
    int8_t iq[MAX_CSI_BYTES];
} event_t;
static QueueHandle_t events;
static atomic_uint queue_drops;

static void enqueue(const event_t *event)
{
    if (xQueueSend(events, event, 0) != pdTRUE) {
        atomic_fetch_add_explicit(&queue_drops, 1, memory_order_relaxed);
    }
}

static void csi_callback(void *ctx, wifi_csi_info_t *info)
{
    (void)ctx;
    if (!info || !info->buf || memcmp(info->mac, TX_MAC, 6) != 0) return;
    if (info->len == 0 || info->len > MAX_CSI_BYTES || info->len % 2) {
        atomic_fetch_add_explicit(&queue_drops, 1, memory_order_relaxed);
        return;
    }
    event_t event = {0};
    event.device_us = info->rx_ctrl.timestamp;
    event.rx_seq = info->rx_seq;
    event.len = info->len;
    event.first_word_invalid = info->first_word_invalid;
    event.rssi = info->rx_ctrl.rssi;
    event.channel = info->rx_ctrl.channel;
    event.sig_mode = info->rx_ctrl.sig_mode;
    event.mcs = info->rx_ctrl.mcs;
    event.cwb = info->rx_ctrl.cwb;
    event.rx_state = info->rx_ctrl.rx_state;
    memcpy(event.iq, info->buf, info->len);
    enqueue(&event); /* Copy immediately; driver-owned pointers are never retained. */
}

static void marker_callback(const esp_now_recv_info_t *info, const uint8_t *data, int len)
{
    if (!info || !info->rx_ctrl || !data || len != sizeof(probe_t)
            || memcmp(info->src_addr, TX_MAC, 6) != 0) return;
    event_t event = {.marker = true, .device_us = info->rx_ctrl->timestamp};
    memcpy(&event.probe, data, sizeof(probe_t));
    if (event.probe.magic != MAGIC || event.probe.reserved != 0) return;
    enqueue(&event);
}

static void logger_task(void *ctx)
{
    (void)ctx;
    event_t event;
    char line[4096];
    while (xQueueReceive(events, &event, portMAX_DELAY) == pdTRUE) {
        int used = snprintf(line, sizeof(line),
                "{\"v\":1,\"kind\":\"%s\",\"device_id\":\"%s\",\"boot_id\":%"PRIu32
                ",\"device_us\":%"PRIu32,
                event.marker ? "MARKER" : "CSI", CONFIG_CSI_DEVICE_ID, boot_id, event.device_us);
        if (event.marker) {
            snprintf(line + used, sizeof(line) - used,
                    ",\"tx_boot_id\":%"PRIu32",\"app_seq\":%"PRIu32",\"tx_us\":%"PRIu64"}",
                    event.probe.boot_id, event.probe.sequence, event.probe.tx_us);
        } else {
            used += snprintf(line + used, sizeof(line) - used,
                    ",\"rx_seq\":%u,\"len\":%u,\"rssi_dbm\":%d,\"noise_floor_dbm\":null"
                    ",\"channel\":%d,\"sig_mode\":%d,\"mcs\":%d,\"cwb\":%d,\"rx_state\":%d"
                    ",\"first_word_invalid\":%s,\"queue_drops\":%u,\"format\":\"lltf_only_v1\",\"iq\":[",
                    (unsigned)event.rx_seq, (unsigned)event.len, event.rssi, event.channel,
                    event.sig_mode, event.mcs, event.cwb, event.rx_state,
                    event.first_word_invalid ? "true" : "false",
                    atomic_load_explicit(&queue_drops, memory_order_relaxed));
            for (unsigned i = 0; i < event.len && used < sizeof(line) - 12; ++i) {
                used += snprintf(line + used, sizeof(line) - used,
                                 "%s%d", i ? "," : "", (int)event.iq[i]);
            }
            snprintf(line + used, sizeof(line) - used, "]}");
        }
        puts(line); /* UART formatting happens in this lower-priority task. */
    }
}
#endif

void app_main(void)
{
    boot_id = esp_random();
    uint8_t local_mac[6] = {0x02, 0, 0, 0, 0, 0};
#ifdef CONFIG_CSI_ROLE_TX
    if (strcmp(CONFIG_CSI_DEVICE_ID, "tx")) abort();
    local_mac[5] = 1;
#else
    if (!strcmp(CONFIG_CSI_DEVICE_ID, "rx-a")) local_mac[5] = 2;
    else if (!strcmp(CONFIG_CSI_DEVICE_ID, "rx-b")) local_mac[5] = 3;
    else abort();
#endif
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    wifi_init_config_t wifi = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&wifi));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_mac(WIFI_IF_STA, local_mac));
    ESP_ERROR_CHECK(esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_11N));
    ESP_ERROR_CHECK(esp_wifi_set_bandwidth(WIFI_IF_STA, WIFI_BW_HT20));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_ERROR_CHECK(esp_wifi_set_ps(WIFI_PS_NONE));
    ESP_ERROR_CHECK(esp_wifi_set_channel(CONFIG_CSI_CHANNEL, WIFI_SECOND_CHAN_NONE));
    ESP_ERROR_CHECK(esp_now_init());
    printf("{\"v\":1,\"kind\":\"BOOT\",\"device_id\":\"%s\",\"boot_id\":%"PRIu32
           ",\"idf\":\"%s\",\"firmware\":\"0.1.0\",\"channel\":%d,\"nominal_rate_hz\":%d}\n",
           CONFIG_CSI_DEVICE_ID, boot_id, esp_get_idf_version(), CONFIG_CSI_CHANNEL, CONFIG_CSI_RATE_HZ);
#ifdef CONFIG_CSI_ROLE_TX
    esp_now_peer_info_t peer = {.channel = CONFIG_CSI_CHANNEL, .ifidx = WIFI_IF_STA, .encrypt = false};
    memcpy(peer.peer_addr, BROADCAST, 6);
    ESP_ERROR_CHECK(esp_now_add_peer(&peer));
    esp_now_rate_config_t rate = {.phymode = WIFI_PHY_MODE_HT20, .rate = WIFI_PHY_RATE_MCS0_LGI,
                                 .ersu = false, .dcm = false};
    ESP_ERROR_CHECK(esp_now_set_peer_rate_config(BROADCAST, &rate));
    TickType_t next = xTaskGetTickCount();
    for (uint32_t seq = 0; ; ++seq) {
        probe_t packet = {.magic = MAGIC, .boot_id = boot_id, .sequence = seq,
                          .tx_us = (uint64_t)esp_timer_get_time()};
        ret = esp_now_send(BROADCAST, (uint8_t *)&packet, sizeof(packet));
        printf("{\"v\":1,\"kind\":\"TX\",\"device_id\":\"tx\",\"boot_id\":%"PRIu32
               ",\"tx_boot_id\":%"PRIu32",\"app_seq\":%"PRIu32",\"tx_us\":%"PRIu64
               ",\"send_status\":%d}\n", boot_id, boot_id, seq, packet.tx_us, (int)ret);
        vTaskDelayUntil(&next, pdMS_TO_TICKS(1000 / CONFIG_CSI_RATE_HZ));
    }
#else
    events = xQueueCreate(32, sizeof(event_t));
    if (!events || xTaskCreate(logger_task, "csi_logger", 8192, NULL, 2, NULL) != pdPASS) abort();
    ESP_ERROR_CHECK(esp_now_register_recv_cb(marker_callback));
    ESP_ERROR_CHECK(esp_wifi_set_promiscuous(true));
    wifi_csi_config_t csi = {.lltf_en = true, .htltf_en = false, .stbc_htltf2_en = false,
                            .ltf_merge_en = false, .channel_filter_en = false,
                            .manu_scale = false, .shift = 0, .dump_ack_en = false};
    ESP_ERROR_CHECK(esp_wifi_set_csi_config(&csi));
    ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(csi_callback, NULL));
    ESP_ERROR_CHECK(esp_wifi_set_csi(true));
#endif
}
