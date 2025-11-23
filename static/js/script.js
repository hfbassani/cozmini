$(document).ready(function () {
    const $inputBox = $("#input_box");
    const $history = $("#history");
    const $cozmoImage = $("#cozmoImageId");
    const $resizeHandle = $("#resize-handle");
    const $container = $("main"); // The flex container
    const $videoSection = $(".video-section");
    const $chatSection = $(".chat-section");

    // Tab management
    let activeTab = localStorage.getItem('cozmo-active-tab') || 'conversation';

    // Resize Logic
    let isResizing = false;

    $resizeHandle.on('mousedown', function (e) {
        isResizing = true;
        $resizeHandle.addClass('active');
        $('body').css('cursor', 'col-resize'); // Prevent cursor flickering
        e.preventDefault();
    });

    $(document).on('mousemove', function (e) {
        if (!isResizing) return;

        const containerOffsetLeft = $container.offset().left;
        const containerWidth = $container.width();
        const pointerRelativeX = e.pageX - containerOffsetLeft;

        // Calculate new widths based on pointer position
        // We want the handle to be centered on the pointer

        // Constrain the resize
        const minVideoWidth = 300;
        const minChatWidth = 400;

        let newVideoWidth = pointerRelativeX - ($resizeHandle.width() / 2);
        let newChatWidth = containerWidth - newVideoWidth - $resizeHandle.width();

        if (newVideoWidth >= minVideoWidth && newChatWidth >= minChatWidth) {
            // Use flex-basis for smoother resizing in flexbox
            const videoFlexBasis = (newVideoWidth / containerWidth) * 100;
            const chatFlexBasis = (newChatWidth / containerWidth) * 100;

            $videoSection.css('flex', `0 0 ${videoFlexBasis}%`);
            $chatSection.css('flex', `0 0 ${chatFlexBasis}%`);
        }
    });

    $(document).on('mouseup', function () {
        if (isResizing) {
            isResizing = false;
            $resizeHandle.removeClass('active');
            $('body').css('cursor', '');
        }
    });

    // Focus input on load
    $inputBox.focus();

    // Tab switching functionality
    function switchTab(tabName) {
        activeTab = tabName;
        localStorage.setItem('cozmo-active-tab', tabName);

        // Update tab buttons
        $('.tab-btn').removeClass('active');
        $(`.tab-btn[data-tab="${tabName}"]`).addClass('active');

        // Filter messages
        if (tabName === 'conversation') {
            // Show only conversation messages (user and Cozmo)
            $('.msg[data-type="conversation"]').show();
            $('.msg[data-type="debug"]').hide();
            $('.api-call, .api-call-error').hide();
        } else {
            // Show everything in debug mode
            $('.msg').show();
            $('.api-call, .api-call-error').show();
        }
    }

    // Initialize tab state
    switchTab(activeTab);

    // Tab click handlers
    $('.tab-btn').on('click', function () {
        const tabName = $(this).data('tab');
        switchTab(tabName);
    });

    // Poll for history updates
    setInterval(function () {
        $.ajax({
            url: getHistoryUrl,
            method: "GET",
            success: function (data) {
                const $statusIndicator = $('.status-indicator').first();
                const $listeningIndicator = $('#listening-indicator');

                // Only restore to connected if we were disconnected (not disconnecting)
                if ($statusIndicator.hasClass('disconnected')) {
                    // Server is back online, restore connected status
                    $statusIndicator.removeClass('disconnected');
                    $statusIndicator.find('.dot').removeClass('disconnected');
                    $('#status-text').text('Connected');
                }

                // Parse history to determine listening state
                const $temp = $('<div>').html(data);
                let isListening = false;
                const $children = $temp.children();

                // Iterate backwards to find the latest relevant event
                for (let i = $children.length - 1; i >= 0; i--) {
                    const text = $($children[i]).text();
                    if (text.includes('cozmo_listens') && text.includes('cozmo started listening')) {
                        isListening = true;
                        break;
                    }
                    if (text.includes('Cozmo stopped listening')) {
                        isListening = false;
                        break;
                    }
                }

                if (isListening) {
                    $listeningIndicator.removeClass('hidden');
                } else {
                    $listeningIndicator.addClass('hidden');
                }

                // Only update if content changed to avoid flickering/unnecessary DOM updates
                // Note: Simple check, can be optimized
                if ($history.html() !== data) {
                    // Check if we were at the bottom before update
                    const isAtBottom = $history.scrollTop() + $history.innerHeight() >= $history[0].scrollHeight - 10;

                    $history.html(data);

                    // Reapply tab filter
                    switchTab(activeTab);

                    // Auto-scroll only if we were already at the bottom
                    if (isAtBottom) {
                        $history.scrollTop($history[0].scrollHeight);
                    }
                }
            },
            error: function () {
                // Connection lost
                const $statusIndicator = $('.status-indicator');

                // Change from disconnecting to disconnected, or from connected to disconnected
                if ($statusIndicator.hasClass('disconnecting')) {
                    $statusIndicator.removeClass('disconnecting');
                    $statusIndicator.find('.dot').removeClass('disconnecting');
                    $statusIndicator.addClass('disconnected');
                    $statusIndicator.find('.dot').addClass('disconnected');
                    $('#status-text').text('Disconnected');
                } else if (!$statusIndicator.hasClass('disconnected')) {
                    $statusIndicator.addClass('disconnected');
                    $statusIndicator.find('.dot').addClass('disconnected');
                    $('#status-text').text('Disconnected');
                }
            }
        });

        // Update image with cache busting
        $cozmoImage.attr("src", "cozmoImage?" + (new Date()).getTime());
    }, 250);

    // Handle input changes (partial input)
    $inputBox.on('input', function () {
        const inputValue = $(this).val();
        $.ajax({
            url: handlePartialInputUrl,
            method: "POST",
            data: {
                current_input: inputValue
            }
        });
    });

    // Handle form submission
    $("#chat-form").on('submit', function (e) {
        e.preventDefault();
        const message = $inputBox.val().trim();

        if (message) {
            $.ajax({
                url: handleInputUrl,
                method: "POST",
                data: {
                    user_says: message
                },
                success: function () {
                    $inputBox.val('');
                    // Force scroll to bottom on send
                    $history.scrollTop($history[0].scrollHeight);
                }
            });
        }
    });
    // Handle Bye button
    $("#bye-btn").on('click', function () {
        if (confirm("Are you sure you want to stop Cozmo?")) {
            $.ajax({
                url: handleInputUrl,
                method: "POST",
                data: {
                    user_says: "bye"
                },
                success: function () {
                    // Update status indicator to disconnecting
                    const $statusIndicator = $('.status-indicator');
                    $statusIndicator.addClass('disconnecting');
                    $statusIndicator.find('.dot').addClass('disconnecting');
                    $('#status-text').text('Disconnecting');
                }
            });
        }
    });
});
