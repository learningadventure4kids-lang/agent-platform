<?php
/**
 * Plugin Name: Kaur AI Agent
 * Description: Embeds an Aria Agent Platform chat widget (any agent, via its public token) on your WordPress site. No Python/Ollama/LangChain runs here -- this plugin only loads the pre-built widget script and points it at your Aria Agent Platform API.
 * Version: 1.0.0
 * Author: Kaur Jewellery
 * License: GPL-2.0-or-later
 * Text Domain: kaur-ai-agent
 */

if (!defined('ABSPATH')) {
    exit; // No direct access.
}

define('KAUR_AI_AGENT_VERSION', '1.0.0');
define('KAUR_AI_AGENT_OPTION', 'kaur_ai_agent_settings');

/**
 * Default settings. `api_url` and `agent_token` are the two things that
 * actually matter -- everything else is presentation.
 */
function kaur_ai_agent_default_settings() {
    return array(
        'api_url'         => 'https://api.example.com',
        'agent_token'     => '',
        'widget_position' => 'floating', // 'floating' or 'inline'
        'enable_widget'   => '1',
        'assistant_name_override' => '', // optional, blank = use agent's configured name
    );
}

function kaur_ai_agent_get_settings() {
    $saved = get_option(KAUR_AI_AGENT_OPTION, array());
    return wp_parse_args($saved, kaur_ai_agent_default_settings());
}

/**
 * Settings page: Settings -> Kaur AI Agent
 */
add_action('admin_menu', function () {
    add_options_page(
        'Kaur AI Agent',
        'Kaur AI Agent',
        'manage_options',
        'kaur-ai-agent',
        'kaur_ai_agent_render_settings_page'
    );
});

add_action('admin_init', function () {
    register_setting('kaur_ai_agent_group', KAUR_AI_AGENT_OPTION, 'kaur_ai_agent_sanitize_settings');
});

function kaur_ai_agent_sanitize_settings($input) {
    $clean = array();
    $clean['api_url'] = isset($input['api_url']) ? esc_url_raw(trim($input['api_url'])) : '';
    $clean['agent_token'] = isset($input['agent_token']) ? sanitize_text_field(trim($input['agent_token'])) : '';
    $clean['widget_position'] = (isset($input['widget_position']) && $input['widget_position'] === 'inline') ? 'inline' : 'floating';
    $clean['enable_widget'] = isset($input['enable_widget']) ? '1' : '0';
    $clean['assistant_name_override'] = isset($input['assistant_name_override']) ? sanitize_text_field($input['assistant_name_override']) : '';
    return $clean;
}

function kaur_ai_agent_render_settings_page() {
    if (!current_user_can('manage_options')) {
        return;
    }
    $settings = kaur_ai_agent_get_settings();
    ?>
    <div class="wrap">
        <h1>Kaur AI Agent</h1>
        <p>
            Public agent tokens are safe to store here -- they only identify which agent
            configuration to load and never expose database, Ollama, or admin credentials.
            Rotate the token from the Aria Agent Platform admin dashboard if it's ever compromised.
        </p>
        <form method="post" action="options.php">
            <?php settings_fields('kaur_ai_agent_group'); ?>
            <table class="form-table" role="presentation">
                <tr>
                    <th scope="row"><label for="kaur_api_url">API URL</label></th>
                    <td>
                        <input type="url" id="kaur_api_url" name="<?php echo esc_attr(KAUR_AI_AGENT_OPTION); ?>[api_url]"
                               value="<?php echo esc_attr($settings['api_url']); ?>" class="regular-text" placeholder="https://api.example.com" required>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="kaur_agent_token">Agent Token</label></th>
                    <td>
                        <input type="text" id="kaur_agent_token" name="<?php echo esc_attr(KAUR_AI_AGENT_OPTION); ?>[agent_token]"
                               value="<?php echo esc_attr($settings['agent_token']); ?>" class="regular-text" placeholder="pub_..." required>
                        <p class="description">The public token for this agent, from the Aria Agent Platform admin dashboard.</p>
                    </td>
                </tr>
                <tr>
                    <th scope="row">Widget Position</th>
                    <td>
                        <label><input type="radio" name="<?php echo esc_attr(KAUR_AI_AGENT_OPTION); ?>[widget_position]" value="floating" <?php checked($settings['widget_position'], 'floating'); ?>> Floating bubble (bottom-right, every page)</label><br>
                        <label><input type="radio" name="<?php echo esc_attr(KAUR_AI_AGENT_OPTION); ?>[widget_position]" value="inline" <?php checked($settings['widget_position'], 'inline'); ?>> Inline only (via the <code>[aria_ai_agent]</code> shortcode)</label>
                    </td>
                </tr>
                <tr>
                    <th scope="row">Enable Widget</th>
                    <td>
                        <label><input type="checkbox" name="<?php echo esc_attr(KAUR_AI_AGENT_OPTION); ?>[enable_widget]" value="1" <?php checked($settings['enable_widget'], '1'); ?>> Enabled</label>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="kaur_assistant_name">Assistant Name (optional override)</label></th>
                    <td>
                        <input type="text" id="kaur_assistant_name" name="<?php echo esc_attr(KAUR_AI_AGENT_OPTION); ?>[assistant_name_override]"
                               value="<?php echo esc_attr($settings['assistant_name_override']); ?>" class="regular-text" placeholder="Leave blank to use the agent's configured name">
                    </td>
                </tr>
            </table>
            <?php submit_button('Save Settings'); ?>
        </form>
    </div>
    <?php
}

/**
 * Shortcode: [aria_ai_agent]
 * Renders an inline mount point. If Widget Position is "floating", the
 * floating bubble is injected site-wide separately (see below) and this
 * shortcode is optional/unused, but still works for embedding an inline
 * copy on a specific page if desired.
 */
add_shortcode('aria_ai_agent', function () {
    $settings = kaur_ai_agent_get_settings();
    if ($settings['enable_widget'] !== '1' || empty($settings['agent_token']) || empty($settings['api_url'])) {
        return '';
    }

    wp_enqueue_script(
        'kaur-ai-agent-widget',
        plugins_url('assets/aria-widget.js', __FILE__),
        array(),
        KAUR_AI_AGENT_VERSION,
        true
    );

    $container_id = 'kaur-ai-agent-' . wp_unique_id();

    ob_start();
    ?>
    <div id="<?php echo esc_attr($container_id); ?>" style="width:100%;max-width:420px;height:560px;"></div>
    <script>
      (function () {
        function mountKaurAiAgent() {
          if (!window.AriaWidget) { return setTimeout(mountKaurAiAgent, 50); }
          window.AriaWidget.mount({
            agentToken: <?php echo wp_json_encode($settings['agent_token']); ?>,
            apiUrl: <?php echo wp_json_encode($settings['api_url']); ?>,
            target: document.getElementById(<?php echo wp_json_encode($container_id); ?>),
          });
        }
        mountKaurAiAgent();
      })();
    </script>
    <?php
    return ob_get_clean();
});

/**
 * Site-wide floating widget (only when Widget Position === 'floating').
 * Uses mountFloating(), which needs no target container and renders its
 * own launcher button + panel via a fixed-position Shadow DOM root.
 */
add_action('wp_footer', function () {
    $settings = kaur_ai_agent_get_settings();
    if ($settings['enable_widget'] !== '1' || $settings['widget_position'] !== 'floating') {
        return;
    }
    if (empty($settings['agent_token']) || empty($settings['api_url'])) {
        return;
    }

    wp_enqueue_script(
        'kaur-ai-agent-widget',
        plugins_url('assets/aria-widget.js', __FILE__),
        array(),
        KAUR_AI_AGENT_VERSION,
        true
    );
    ?>
    <script>
      (function () {
        function mountKaurAiAgentFloating() {
          if (!window.AriaWidget) { return setTimeout(mountKaurAiAgentFloating, 50); }
          window.AriaWidget.mountFloating({
            agentToken: <?php echo wp_json_encode($settings['agent_token']); ?>,
            apiUrl: <?php echo wp_json_encode($settings['api_url']); ?>,
          });
        }
        mountKaurAiAgentFloating();
      })();
    </script>
    <?php
});
