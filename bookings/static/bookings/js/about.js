document.addEventListener("DOMContentLoaded", () => {
    
    // =========================================================================
    // 1. DYNAMIC INCREMENTAL COUNTER ENGINE
    // =========================================================================
    const speed = 200; // Counter progression divisor rate
    const counterElements = document.querySelectorAll(".metric-number");

    const runCounters = (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counter = entry.target;
                const targetValue = parseInt(counter.getAttribute("data-target"), 10);
                
                const updateCount = () => {
                    const currentCount = parseInt(counter.innerText, 10);
                    const increment = Math.ceil(targetValue / speed);

                    if (currentCount < targetValue) {
                        counter.innerText = currentCount + increment > targetValue ? targetValue + "+" : (currentCount + increment);
                        setTimeout(updateCount, 15);
                    } else {
                        counter.innerText = targetValue + "+";
                    }
                };

                updateCount();
                observer.unobserve(counter); // Disconnect observation loop once transaction executes
            }
        });
    };

    const counterObserver = new IntersectionObserver(runCounters, {
        threshold: 0.5,
        rootMargin: "0px 0px -50px 0px"
    });

    counterElements.forEach(element => counterObserver.observe(element));
});