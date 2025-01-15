export function executeWithHooks(func, options = {}) {
    return function (...args) {
        // Initialize the state object with the original arguments
        const state = { args }

        // Call the before hook if it exists, passing the state object
        if (options.before && typeof options.before === 'function') {
            options.before.apply(this, [state])
        }

        // Execute the main function with the arguments from the state object
        state.result = func(...state.args)

        // Call the after hook if it exists, passing the updated state object
        if (options.after && typeof options.after === 'function') {
            options.after.apply(this, [state])
        }

        // Return the result stored in the state object
        return state.result
    }
}

export async function executeWithHooksAsync(func, options = {}) {
    return async function (...args) {
        // Initialize the state object with the original arguments
        const state = { args }

        // Call the before hook if it exists, passing the state object
        if (options.before && typeof options.before === 'function') {
            await options.before.apply(this, [state])
        }

        // Execute the main function with the arguments from the state object
        state.result = await func(...state.args)

        // Call the after hook if it exists, passing the updated state object
        if (options.after && typeof options.after === 'function') {
            await options.after.apply(this, [state])
        }

        // Return the result stored in the state object
        return state.result
    }
}
